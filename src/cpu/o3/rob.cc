/*
 * Copyright (c) 2012 ARM Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder.  You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2004-2006 The Regents of The University of Michigan
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are
 * met: redistributions of source code must retain the above copyright
 * notice, this list of conditions and the following disclaimer;
 * redistributions in binary form must reproduce the above copyright
 * notice, this list of conditions and the following disclaimer in the
 * documentation and/or other materials provided with the distribution;
 * neither the name of the copyright holders nor the names of its
 * contributors may be used to endorse or promote products derived from
 * this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 * "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 * LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
 * A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
 * OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
 * SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
 * LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
 * OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "cpu/o3/rob.hh"

#include <list>

#include "base/logging.hh"
#include "cpu/o3/dyn_inst.hh"
#include "cpu/o3/dyn_inst_ptr.hh"
#include "cpu/o3/limits.hh"
#include "debug/Fetch.hh"
#include "debug/O3PipeView.hh"
#include "debug/ROB.hh"
#include "params/BaseO3CPU.hh"

namespace gem5
{

namespace o3
{

ROB::ROB(CPU *_cpu, PhysRegFile* _regfile, const BaseO3CPUParams &params)
    : robPolicy(params.smtROBPolicy),
      cpu(_cpu),
      regFile(_regfile),
      numEntries(params.numROBEntries),
      squashWidth(params.squashWidth),
      numInstsInROB(0),
      numThreads(params.numThreads),
      stats(_cpu)
{
    //Figure out rob policy
    if (robPolicy == SMTQueuePolicy::Dynamic) {
        //Set Max Entries to Total ROB Capacity
        for (ThreadID tid = 0; tid < numThreads; tid++) {
            maxEntries[tid] = numEntries;
        }

    } else if (robPolicy == SMTQueuePolicy::Partitioned) {
        DPRINTF(Fetch, "ROB sharing policy set to Partitioned\n");

        //@todo:make work if part_amt doesnt divide evenly.
        int part_amt = numEntries / numThreads;

        //Divide ROB up evenly
        for (ThreadID tid = 0; tid < numThreads; tid++) {
            maxEntries[tid] = part_amt;
        }

    } else if (robPolicy == SMTQueuePolicy::Threshold) {
        DPRINTF(Fetch, "ROB sharing policy set to Threshold\n");

        int threshold =  params.smtROBThreshold;;

        //Divide up by threshold amount
        for (ThreadID tid = 0; tid < numThreads; tid++) {
            maxEntries[tid] = threshold;
        }
    }

    for (ThreadID tid = numThreads; tid < MaxThreads; tid++) {
        maxEntries[tid] = 0;
    }

    resetState();
}

void
ROB::resetState()
{
    for (ThreadID tid = 0; tid  < MaxThreads; tid++) {
        threadEntries[tid] = 0;
        squashIt[tid] = instList[tid].end();
        squashedSeqNum[tid] = 0;
        doneSquashing[tid] = true;
    }
    numInstsInROB = 0;

    // Initialize the "universal" ROB head & tail point to invalid
    // pointers
    head = instList[0].end();
    tail = instList[0].end();
}

std::string
ROB::name() const
{
    return cpu->name() + ".rob";
}

void
ROB::setActiveThreads(std::list<ThreadID> *at_ptr)
{
    DPRINTF(ROB, "Setting active threads list pointer.\n");
    activeThreads = at_ptr;
}

void
ROB::drainSanityCheck() const
{
    for (ThreadID tid = 0; tid  < numThreads; tid++)
        assert(instList[tid].empty());
    assert(isEmpty());
}

void
ROB::takeOverFrom()
{
    resetState();
}

void
ROB::resetEntries()
{
    if (robPolicy != SMTQueuePolicy::Dynamic || numThreads > 1) {
        auto active_threads = activeThreads->size();

        std::list<ThreadID>::iterator threads = activeThreads->begin();
        std::list<ThreadID>::iterator end = activeThreads->end();

        while (threads != end) {
            ThreadID tid = *threads++;

            if (robPolicy == SMTQueuePolicy::Partitioned) {
                maxEntries[tid] = numEntries / active_threads;
            } else if (robPolicy == SMTQueuePolicy::Threshold &&
                       active_threads == 1) {
                maxEntries[tid] = numEntries;
            }
        }
    }
}

int
ROB::entryAmount(ThreadID num_threads)
{
    if (robPolicy == SMTQueuePolicy::Partitioned) {
        return numEntries / num_threads;
    } else {
        return 0;
    }
}

int
ROB::countInsts()
{
    int total = 0;

    for (ThreadID tid = 0; tid < numThreads; tid++)
        total += countInsts(tid);

    return total;
}

size_t
ROB::countInsts(ThreadID tid)
{
    return instList[tid].size();
}

void
ROB::insertInst(const DynInstPtr &inst)
{
    assert(inst);

    stats.writes++;

    if (inst->isWriteBarrier() && inst->isReadBarrier()) {
        mfence = true;
        lfence_en = false;
    } else if (inst->isReadBarrier() && mfence) {
        lfence_en = true;
        mfence = false;
    }



    if (inst->isSyscall()) {
        stats.syscalls++;
    }

    DPRINTF(ROB, "Adding inst PC %s "
                 "[sn:%llu] to the ROB.\n",
                 inst->pcState(), inst->seqNum);

    if (inst->isOkapiReset()) {
        DPRINTF(ROB, "Okapi reset encountered inst PC %s "
                     "[sn:%llu].\n",
                inst->pcState(), inst->seqNum);
    }


    assert(numInstsInROB != numEntries);

    ThreadID tid = inst->threadNumber;

    instList[tid].push_back(inst);

    //Set Up head iterator if this is the 1st instruction in the ROB
    if (numInstsInROB == 0) {
        head = instList[tid].begin();
        assert((*head) == inst);
    }

    //Must Decrement for iterator to actually be valid  since __.end()
    //actually points to 1 after the last inst
    tail = instList[tid].end();
    tail--;

    inst->setInROB();

    if (inst->isLoad()) {
        stats.loads++;
        if (cpu->getSpeculativeLoadPolicy() ==
        SpeculativeLoadPolicy::NaiveDelay) {
            DPRINTF(ROB, "Marking load inst PC %s "
                         "[sn:%llu] as unsafe.\n",
                         inst->pcState(), inst->seqNum);
            inst->setUnsafeLoad();
            if (inst == (*head)) {
                inst->clearUnsafeLoad();
                DPRINTF(ROB, "Immediately clear unsafe load inst PC "
                             "%s [sn:%llu] because it is at head.\n",
                             inst->pcState(), inst->seqNum);
            }
        }
        else if (cpu->getSpeculativeLoadPolicy() ==
        SpeculativeLoadPolicy::EagerDelay) {
            if (instIsShadowed(inst, tid)) {
                DPRINTF(ROB, "Marking load inst PC %s "
                             "[sn:%llu] as unsafe.\n",
                             inst->pcState(), inst->seqNum);
                inst->setUnsafeLoad();
                inst->setShadowed();
            }
        }  else if (cpu->getSpeculativeLoadPolicy() ==
           SpeculativeLoadPolicy::Okapi) {
            olderOkapiReset(inst, tid);
            if (instIsShadowed(inst, tid)) {
                DPRINTF(ROB, "Marking load inst PC %s "
                             "[sn:%llu] as unsafe under Okapi.\n",
                             inst->pcState(), inst->seqNum);
                inst->setUnsafeLoad();
                inst->setOkapiLoad();
                stats.okapiV1Loads++;
                inst->setShadowed();
            }
            if (instIsV2Vulnerability(inst, tid)) {
                DPRINTF(ROB, "Marking load inst PC %s "
                             "[sn:%llu] as v2 unsafe under Okapi.\n",
                        inst->pcState(), inst->seqNum);
                inst->setUnsafeLoad();
                inst->setOkapiV2Load();
                inst->setShadowed();
                stats.okapiV2Loads++;
            }
            if (inst->isOkapiV2Load() && !inst->isOkapiLoad()) assert (0);
            if (inst->isUnsafeLoad()) stats.okapiLoads++;
        }
        else if (cpu->getSpeculativeLoadPolicy() ==
        SpeculativeLoadPolicy::STT) {
            if (instIsShadowed(inst, tid)) {
                /** [Schmitz, STT] if the instruction is
                 * a shadowed load -> initialize the taint and the YRoT */
                DPRINTF(ROB, "Initialize taint for load "
                             "inst PC %s [sn:%llu].\n",
                             inst->pcState(), inst->seqNum);
                stats.taints++;
                inst->isDestTainted(true);
                taintDestinations(inst, inst->seqNum);
            }
        }
    }

    if (cpu->getSpeculativeLoadPolicy() == SpeculativeLoadPolicy::STT) {
        //propagate taint
        std::set<InstSeqNum> yRoT_candidates;
        bool tainted = false;
        for (int i = 0; i < inst->numSrcRegs(); i++) {
            if (inst->srcRegIdx(i).index() == 16)
                // exclude zero register (zero register cannot be tainted)
                continue;
            if (regFile->getTaint(inst->renamedSrcIdx(i))) {
                tainted = true;
                //mark inst to be blocked if >= 1 argument is tainted
                inst->isArgsTainted(true);
                yRoT_candidates.emplace(
                        regFile->getYRoT(inst->renamedSrcIdx(i)));
            }
        }

        if (tainted) {
            if (inst->isCondCtrl()) stats.branches_with_tainted_args++;
            //if the instruction operates with
            // tainted arguments taint the destinations as well
            DPRINTF(ROB, "Propagate taint for "
                         "inst PC %s [sn:%llu] with yRoT %llu.\n",
                    inst->pcState(), inst->seqNum,
                    *(yRoT_candidates.rbegin()));
            taintDestinations(inst, *(yRoT_candidates.rbegin()));
        }
    }

    ++numInstsInROB;
    ++threadEntries[tid];

    assert((*tail) == inst);

    DPRINTF(ROB, "[tid:%i] Now has %d instructions.\n", tid,
            threadEntries[tid]);
}

void
ROB::retireHead(ThreadID tid)
{
    stats.writes++;

    assert(numInstsInROB > 0);

    // Get the head ROB instruction by copying it and remove it from the list
    InstIt head_it = instList[tid].begin();

    DynInstPtr head_inst = std::move(*head_it);
    instList[tid].erase(head_it);

    assert(head_inst->readyToCommit());

    DPRINTF(ROB, "[tid:%i] Retiring head instruction, "
            "instruction PC %s, [sn:%llu]\n", tid, head_inst->pcState(),
            head_inst->seqNum);

    if (cpu->getSpeculativeLoadPolicy() == SpeculativeLoadPolicy::STT) {
        //!Untaint retiring YRoTs ...
        std::vector<InstSeqNum> unshadowedYRoTs;
        unshadowedYRoTs.push_back(head_inst->seqNum);
        regFile->clearYRoTsAndTaints(unshadowedYRoTs);
    }

    --numInstsInROB;
    --threadEntries[tid];

    head_inst->clearInROB();
    head_inst->setCommitted();

    //Update "Global" Head of ROB
    updateHead();

    // @todo: A special case is needed if the instruction being
    // retired is the only instruction in the ROB; otherwise the tail
    // iterator will become invalidated.
    cpu->removeFrontInst(head_inst);
}

std::optional<ROB::Shadow>
ROB::instCastsShadow(const DynInstPtr& inst, bool v2)
{
    // C-Shadow
    if (inst->isControl() && !(inst->isExecuted() && !inst->mispredicted())) {
        return {{Shadow::Type::C}};
    }

    // Only cast C-Shadows in relaxed policy
    if ((cpu->getThreatModel() == ThreatModel::Spectre) || v2)
        return std::nullopt;

    // D-Shadow
    if (inst->isStore() && !inst->translationCompleted()) {
        return {{Shadow::Type::D}};
    }

    // E-Shadow
    bool isMemoryAccessThatMightFail =
            (inst->isLoad() || inst->isStore()) &&
            !inst->translationCompleted();
    if (!inst->isExecuted() && (isMemoryAccessThatMightFail ||
                                inst->isSyscall() || inst->isFloating())) {
        return {{Shadow::Type::E}};
    }

    // M-Shadow
    if (!inst->isExecuted() && inst->isLoad()) {
        return {{Shadow::Type::M}};
    }

    return std::nullopt;
}

std::optional<ROB::Shadow>
ROB::instCastsV2Shadow(DynInstPtr inst)
{
    // C-Shadow
    if (inst->isV2Suspicious() &&
        !(inst->isExecuted() && !inst->mispredicted())) {
        return {{Shadow::Type::V2}};
    }
    return std::nullopt;
}

bool
ROB::instIsShadowed(DynInstPtr inst, ThreadID tid, bool v2)
{
    bool shadowed = false;
    if (cpu->getThreatModel() == ThreatModel::Naive) {
        if (inst != (*head)) return true;
    }
    for (const auto& instIt : instList[tid])
    {
        auto shadow = instCastsShadow(instIt, v2);
        if (shadow) {
            DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                         "[sn:%llu] casts %s-Shadow\n",
                         tid, instIt->pcState(),
                         instIt->seqNum, shadow->toString());

            // Don't cast shadow on itself
            if (instIt != inst) {
                shadowed = true;
                break;
            }
        }
        DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                     "[sn:%llu] does not cast a Shadow\n",
                tid, instIt->pcState(),
                instIt->seqNum, shadow->toString());

        if (inst == instIt) break; //only check for shadows until inst itself
    }
    return shadowed;
}

bool
ROB::instIsV2Vulnerability(DynInstPtr inst, ThreadID tid)
{
    bool v2 = false;
    for (const auto& instIt : instList[tid])
    {
        //older inst is v2 suspicious
        if (instIt->isV2Suspicious()) {
            DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                 "[sn:%llu] casts V2-Shadow\n",
            tid, instIt->pcState(),instIt->seqNum);
            //Check if the older instruction is shadowed by sth else
            if (instIsShadowed(instIt, tid)) {
                DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                             "[sn:%llu] casts V2-Shadow "
                             "and is shadowed itself\n",
                        tid, instIt->pcState(),
                        instIt->seqNum);
                // Don't cast shadow on itself
                if (instIt != inst) {
                    v2 = true;
                    break;
                }

            }
        } else {
            DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                         "[sn:%llu] does not cast V2-Shadow\n",
                    tid, instIt->pcState(),instIt->seqNum);
        }
        if (instIt == inst) break; //we only need to iterate from head to inst
        /*auto _v2 = instCastsV2Shadow(instIt);
        if (_v2) {
            DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                         "[sn:%llu] casts V2 %s-Shadow\n",
                    tid, instIt->pcState(),
                    instIt->seqNum, _v2->toString());

            // Don't cast shadow on itself
            if (instIt != inst) {
                v2 = true;
                break;
            }
        }*/
    }
    return v2;
}

void
ROB::olderOkapiReset(DynInstPtr inst, ThreadID tid)
{
    for (const auto& instIt : instList[tid])
    {
        //! Floating Point NOP is re-used for Okapi Reset
        if ((instIt->isOkapiReset()
            || instIt->isSyscall()) && !instIt->isExecuted()) {
        //if ((instIt->isOkapiReset()) && !instIt->isExecuted()) {
            inst->setOkapiResetSuccessor();
            DPRINTF(ROB, "[tid:%i] Instruction PC %s "
                         "[sn:%llu] is an FNOP and thus "
                         "Instruction PC %s [sn:%llu]"
                         " won't be speculated on\n",
                    tid, instIt->pcState(),
                    instIt->seqNum, inst->pcState(), inst->seqNum);
            break;
        }
    }
}

void
ROB::taintDestinations(DynInstPtr inst, InstSeqNum yRoT)
{
    inst->isDestTainted(true);
    for (int i = 0; i < inst->numDestRegs(); i++) {
        regFile->setTaint(inst->renamedDestIdx(i), true);
        regFile->setYRoT(inst->renamedDestIdx(i), yRoT);
    }
}

std::vector<DynInstPtr>
ROB::updateShadowedInsts(ThreadID tid)
{
    DPRINTF(ROB, "[tid:%i] Try to unshadow instructions.\n", tid);
    std::vector<DynInstPtr> unshadowedInsts;

    //iterate through the ROB
    for (const auto& instIt : instList[tid])
    {
        // Don't cast shadow on ROB head
        if (instIt != instList[tid].front()) {
            auto shadow = instCastsShadow(instIt);
            if (shadow) {
                DPRINTF(ROB, "[tid:%i] Instruction PC %s"
                             " [sn:%llu] casts %s-Shadow\n",
                             tid, instIt->pcState(),
                             instIt->seqNum, shadow->toString());
                if (instIt->isUnsafeLoad()) {
                    DPRINTF(ROB, "Unshadow shadowing inst itself PC %s "
                                 "[sn:%llu].\n",
                            instIt->pcState(), instIt->seqNum);
                    instIt->clearUnsafeLoad();
                    unshadowedInsts.push_back(instIt);
                }
                break;
            }
        }

        if (instIt->isUnsafeLoad())
        {
            DPRINTF(ROB, "Unshadow inst PC %s "
                         "[sn:%llu].\n",
                         instIt->pcState(), instIt->seqNum);
            instIt->clearUnsafeLoad();
            unshadowedInsts.push_back(instIt);

#if TRACING_ON
            if (debug::O3PipeView) {
                instIt->safeTick = curTick() - instIt->fetchTick;
            }
#endif
        }
    }

    DPRINTF(ROB, "[tid:%i] Try to unshadow V2 instructions.\n", tid);
    //! find the first v2 suspicious instruction behind C shadow
    bool found_unsafe = false;
    for (auto instIt : instList[tid])
    {
        // Don't cast shadow on ROB head
        if (instIt != instList[tid].front()) {
            auto shadow = instCastsShadow(instIt, true);
            if (shadow) {
                DPRINTF(ROB, "[tid:%i] Instruction PC %s"
                             " [sn:%llu] casts %s-Shadow\n",
                        tid, instIt->pcState(),
                        instIt->seqNum, shadow->toString());

                found_unsafe = true;
            }
        }

        //stop clearing when first suspicious inst after shadow is encountered
        if (found_unsafe && instIt->isV2Suspicious()) break;

        if (instIt->isOkapiV2Load())
        {
            DPRINTF(ROB, "V2 Unshadow inst PC %s "
                         "[sn:%llu].\n",
                    instIt->pcState(), instIt->seqNum);
            //instIt->clearUnsafeLoad();
            instIt->clearOkapiV2Load();
            //unshadowedInsts.push_back(instIt);

        }

    }

    return unshadowedInsts;
}

bool
ROB::isHeadReady(ThreadID tid)
{
    stats.reads++;
    if (threadEntries[tid] != 0) {
        return instList[tid].front()->readyToCommit();
    }

    return false;
}

bool
ROB::canCommit()
{
    //@todo: set ActiveThreads through ROB or CPU
    std::list<ThreadID>::iterator threads = activeThreads->begin();
    std::list<ThreadID>::iterator end = activeThreads->end();

    while (threads != end) {
        ThreadID tid = *threads++;

        if (isHeadReady(tid)) {
            return true;
        }
    }

    return false;
}

unsigned
ROB::numFreeEntries()
{
    return numEntries - numInstsInROB;
}

unsigned
ROB::numFreeEntries(ThreadID tid)
{
    return maxEntries[tid] - threadEntries[tid];
}

void
ROB::doSquash(ThreadID tid)
{
    stats.writes++;
    DPRINTF(ROB, "[tid:%i] Squashing instructions until [sn:%llu].\n",
            tid, squashedSeqNum[tid]);

    assert(squashIt[tid] != instList[tid].end());

    if ((*squashIt[tid])->seqNum < squashedSeqNum[tid]) {
        DPRINTF(ROB, "[tid:%i] Done squashing instructions.\n",
                tid);

        squashIt[tid] = instList[tid].end();

        doneSquashing[tid] = true;
        return;
    }

    bool robTailUpdate = false;

    unsigned int numInstsToSquash = squashWidth;

    // If the CPU is exiting, squash all of the instructions
    // it is told to, even if that exceeds the squashWidth.
    // Set the number to the number of entries (the max).
    if (cpu->isThreadExiting(tid))
    {
        numInstsToSquash = numEntries;
    }

    for (int numSquashed = 0;
         numSquashed < numInstsToSquash &&
         squashIt[tid] != instList[tid].end() &&
         (*squashIt[tid])->seqNum > squashedSeqNum[tid];
         ++numSquashed)
    {
        DPRINTF(ROB, "[tid:%i] Squashing instruction PC %s, seq num %i.\n",
                (*squashIt[tid])->threadNumber,
                (*squashIt[tid])->pcState(),
                (*squashIt[tid])->seqNum);

        if (!(*squashIt[tid])->isIssued())
            stats.okapiLoadsSquashedBeforeIssue++;

        // Mark the instruction as squashed, and ready to commit so that
        // it can drain out of the pipeline.
        (*squashIt[tid])->setSquashed();

        (*squashIt[tid])->setCanCommit();

        auto squashed_inst = (*squashIt[tid]);
        if (cpu->getSpeculativeLoadPolicy() == SpeculativeLoadPolicy::STT) {
            for (int i = 0; i < squashed_inst->numDestRegs(); i++) {
                // exclude zero register (zero register cannot be tainted)
                if (squashed_inst->destRegIdx(i).index() == 16)
                    continue;
                //!Untaint squashed YRoTs ...
                //! only untaint if the yrot of the
                //! dest reg is still the instruction ID.
                if (regFile->getTaint(squashed_inst->renamedDestIdx(i))) {
                    if (regFile->getYRoT(squashed_inst->renamedDestIdx(i)) ==
                      squashed_inst->seqNum) {
                        regFile->setTaint(
                                squashed_inst->renamedSrcIdx(i), false);
                        regFile->setYRoT(squashed_inst->renamedSrcIdx(i), 0);
                    }
                }

            }
            std::vector<InstSeqNum> unshadowedYRoTs;
            unshadowedYRoTs.push_back(squashed_inst->seqNum);
            regFile->clearYRoTsAndTaints(unshadowedYRoTs);
        }

        if (squashIt[tid] == instList[tid].begin()) {
            DPRINTF(ROB, "Reached head of instruction list while "
                    "squashing.\n");

            squashIt[tid] = instList[tid].end();

            doneSquashing[tid] = true;

            return;
        }

        InstIt tail_thread = instList[tid].end();
        tail_thread--;

        if ((*squashIt[tid]) == (*tail_thread))
            robTailUpdate = true;

        squashIt[tid]--;
    }


    // Check if ROB is done squashing.
    if ((*squashIt[tid])->seqNum <= squashedSeqNum[tid]) {
        DPRINTF(ROB, "[tid:%i] Done squashing instructions.\n",
                tid);

        squashIt[tid] = instList[tid].end();

        doneSquashing[tid] = true;
    }

    if (robTailUpdate) {
        updateTail();
    }
}


void
ROB::updateHead()
{
    InstSeqNum lowest_num = 0;
    bool first_valid = true;

    // @todo: set ActiveThreads through ROB or CPU
    std::list<ThreadID>::iterator threads = activeThreads->begin();
    std::list<ThreadID>::iterator end = activeThreads->end();

    while (threads != end) {
        ThreadID tid = *threads++;

        if (instList[tid].empty())
            continue;

        if (first_valid) {
            head = instList[tid].begin();
            lowest_num = (*head)->seqNum;
            first_valid = false;
            continue;
        }

        InstIt head_thread = instList[tid].begin();

        DynInstPtr head_inst = (*head_thread);

        assert(head_inst != 0);

        if (head_inst->seqNum < lowest_num) {
            head = head_thread;
            lowest_num = head_inst->seqNum;
        }
    }

    if (first_valid) {
        head = instList[0].end();
    }

    if ((*head)) {
        DPRINTF(ROB, "head inst is [sn:%llu]\n",
                (*head)->seqNum);
        if (cpu->getSpeculativeLoadPolicy() ==
          SpeculativeLoadPolicy::NaiveDelay) {
            (*head)->clearUnsafeLoad();
            DPRINTF(ROB, "Clear unsafe load bit for "
                         "load instruction at head [sn:%llu]\n",
                         (*head)->seqNum);
        }
    }

}

void
ROB::updateTail()
{
    tail = instList[0].end();
    bool first_valid = true;

    std::list<ThreadID>::iterator threads = activeThreads->begin();
    std::list<ThreadID>::iterator end = activeThreads->end();

    while (threads != end) {
        ThreadID tid = *threads++;

        if (instList[tid].empty()) {
            continue;
        }

        // If this is the first valid then assign w/out
        // comparison
        if (first_valid) {
            tail = instList[tid].end();
            tail--;
            first_valid = false;
            continue;
        }

        // Assign new tail if this thread's tail is younger
        // than our current "tail high"
        InstIt tail_thread = instList[tid].end();
        tail_thread--;

        if ((*tail_thread)->seqNum > (*tail)->seqNum) {
            tail = tail_thread;
        }
    }
}


void
ROB::squash(InstSeqNum squash_num, ThreadID tid)
{
    if (isEmpty(tid)) {
        DPRINTF(ROB, "Does not need to squash due to being empty "
                "[sn:%llu]\n",
                squash_num);

        return;
    }

    DPRINTF(ROB, "Starting to squash within the ROB.\n");

    robStatus[tid] = ROBSquashing;

    doneSquashing[tid] = false;

    squashedSeqNum[tid] = squash_num;

    if (!instList[tid].empty()) {
        InstIt tail_thread = instList[tid].end();
        tail_thread--;

        squashIt[tid] = tail_thread;

        doSquash(tid);
    }
}

const DynInstPtr&
ROB::readHeadInst(ThreadID tid)
{
    if (threadEntries[tid] != 0) {
        InstIt head_thread = instList[tid].begin();

        assert((*head_thread)->isInROB());

        return *head_thread;
    } else {
        return dummyInst;
    }
}

DynInstPtr
ROB::readTailInst(ThreadID tid)
{
    InstIt tail_thread = instList[tid].end();
    tail_thread--;

    return *tail_thread;
}

ROB::ROBStats::ROBStats(statistics::Group *parent)
  : statistics::Group(parent, "rob"),
    ADD_STAT(reads, statistics::units::Count::get(),
        "The number of ROB reads"),
    ADD_STAT(writes, statistics::units::Count::get(),
        "The number of ROB writes"),
    ADD_STAT(loads, statistics::units::Count::get(),
             "The number of loads in the ROB"),
    ADD_STAT(okapiLoads, statistics::units::Count::get(),
             "The number of unsafe loads under Okapi"),
    ADD_STAT(taints, statistics::units::Count::get(),
             "The number of taints initialized in the ROB"),
    ADD_STAT(branches_with_tainted_args, statistics::units::Count::get(),
             "The number of branches with tainted args"),
    ADD_STAT(syscalls, statistics::units::Count::get(),
             "The number of syscalls inserted into the ROB"),
    ADD_STAT(okapiV2Loads, statistics::units::Count::get(),
             "The number of loads that are unsafe under"
             " the futuristic model inserted in the ROB"),
    ADD_STAT(okapiV1Loads, statistics::units::Count::get(),
             "The number of loads that are unsafe"
             " under the spectre model inserted in the ROB")

{
}

DynInstPtr
ROB::findInst(ThreadID tid, InstSeqNum squash_inst)
{
    for (InstIt it = instList[tid].begin(); it != instList[tid].end(); it++) {
        if ((*it)->seqNum == squash_inst) {
            return *it;
        }
    }
    return NULL;
}

void
ROB::compute_taint(ThreadID tid)
{
    assert(cpu->getSpeculativeLoadPolicy() == SpeculativeLoadPolicy::STT);
    DPRINTF(ROB, "[tid:%i] Try to unshadow instructions.\n", tid);
    std::vector<DynInstPtr> unshadowedInsts;
    std::vector<InstSeqNum> unshadowedYRoTs;
    //! Collect all Access instructions that are bound to commit
    for (const auto& instIt : instList[tid])
    {
        // Don't cast shadow on ROB head
        if (instIt != instList[tid].front()) {
            auto shadow = instCastsShadow(instIt);
            if (shadow) {
                DPRINTF(
                        ROB,
                        "[tid:%i] Instruction PC %s [sn:%llu]"
                        " casts %s-Shadow\n",
                        tid, instIt->pcState(),
                        instIt->seqNum, shadow->toString());

                break;
            }
        }

        if ((instIt->isDestTainted()) && instIt->isAccess())
        {
            DPRINTF(ROB, "Unshadow inst PC %s [sn:%llu].\n"
                    , instIt->pcState(), instIt->seqNum);
            instIt->isDestTainted(false);
            //instIt->isArgsTainted(false);
            unshadowedInsts.push_back(instIt);
            unshadowedYRoTs.push_back(instIt->seqNum);
        }
    }
    //! Clear the taints caused by these access instructions in the regfile
    regFile->clearYRoTsAndTaints(unshadowedYRoTs);

    //! Untaint the instructions themselves
    for (const auto& instIt : instList[tid])
    {
        bool tainted = false;
        for (int i = 0; i < instIt->numSrcRegs(); i++) {
            //zero reg cannot be taintes
            if (instIt->srcRegIdx(i).index() == 16)
                continue;
            if (regFile->getTaint(instIt->renamedSrcIdx(i))) {
                tainted = true;
                instIt->isArgsTainted(true);
            }
        }
        if (!tainted) {
            instIt->isArgsTainted(false);
            instIt->isDestTainted(false);
        }

    }
}


} // namespace o3
} // namespace gem5
