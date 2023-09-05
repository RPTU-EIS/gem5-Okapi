/*
 * Copyright (c) 2016-2018 ARM Limited
 * All rights reserved
 *
 * The license below extends only to copyright in the software and shall
 * not be construed as granting a license to any other intellectual
 * property including but not limited to intellectual property relating
 * to a hardware implementation of the functionality of the software
 * licensed hereunder. You may use the software subject to the license
 * terms below provided that you ensure that this notice is replicated
 * unmodified and in its entirety in all distributions of the software,
 * modified or unmodified, in source code or in binary form.
 *
 * Copyright (c) 2004-2005 The Regents of The University of Michigan
 * Copyright (c) 2013 Advanced Micro Devices, Inc.
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

#ifndef __CPU_O3_REGFILE_HH__
#define __CPU_O3_REGFILE_HH__

#include <cstring>
#include <vector>

#include "arch/generic/isa.hh"
#include "base/trace.hh"
#include "cpu/o3/comm.hh"
#include "cpu/regfile.hh"
#include "debug/IEW.hh"

namespace gem5
{

namespace o3
{

class UnifiedFreeList;

/**
 * Simple physical register file class.
 */
class PhysRegFile
{
  private:

    using PhysIds = std::vector<PhysRegId>;
  public:
    using IdRange = std::pair<PhysIds::iterator,
                              PhysIds::iterator>;
  private:
    /** Integer register file. */
    RegFile intRegFile;
    std::vector<PhysRegId> intRegIds;
    std::vector<bool> intRegTaints;
    std::vector<InstSeqNum> intRegYRoTs;

    /** Floating point register file. */
    RegFile floatRegFile;
    std::vector<PhysRegId> floatRegIds;
    std::vector<bool> floatRegTaints;
    std::vector<InstSeqNum> floatRegYRoTs;

    /** Vector register file. */
    RegFile vectorRegFile;
    std::vector<PhysRegId> vecRegIds;
    std::vector<bool> vectorRegTaints;
    std::vector<InstSeqNum> vectorRegYRoTs;

    /** Vector element register file. */
    RegFile vectorElemRegFile;
    std::vector<PhysRegId> vecElemIds;
    std::vector<bool> vecElemRegTaints;
    std::vector<InstSeqNum> vecElemRegYRoTs;

    /** Predicate register file. */
    RegFile vecPredRegFile;
    std::vector<PhysRegId> vecPredRegIds;
    std::vector<bool> vecPredTaints;
    std::vector<InstSeqNum> vecPredRegYRoTs;

    /** Matrix register file. */
    RegFile matRegFile;
    std::vector<PhysRegId> matRegIds;
    std::vector<bool> matRegTaints;
    std::vector<InstSeqNum> matRegYRoTs;

    /** Condition-code register file. */
    RegFile ccRegFile;
    std::vector<PhysRegId> ccRegIds;
    std::vector<bool> ccRegTaints;
    std::vector<InstSeqNum> ccRegYRoTs;

    /** Misc Reg Ids */
    std::vector<PhysRegId> miscRegIds;
    std::vector<bool> miscRegTaints;
    std::vector<InstSeqNum> miscRegYRoTs;

    /**
     * Number of physical general purpose registers
     */
    unsigned numPhysicalIntRegs;

    /**
     * Number of physical floating point registers
     */
    unsigned numPhysicalFloatRegs;

    /**
     * Number of physical vector registers
     */
    unsigned numPhysicalVecRegs;

    /**
     * Number of physical vector element registers
     */
    unsigned numPhysicalVecElemRegs;

    /**
     * Number of physical predicate registers
     */
    unsigned numPhysicalVecPredRegs;

    /**
     * Number of physical matrix registers
     */
    unsigned numPhysicalMatRegs;

    /**
     * Number of physical CC registers
     */
    unsigned numPhysicalCCRegs;

    /** Total number of physical registers. */
    unsigned totalNumRegs;

  public:
    /**
     * Constructs a physical register file with the specified amount of
     * integer and floating point registers.
     */
    PhysRegFile(unsigned _numPhysicalIntRegs,
                unsigned _numPhysicalFloatRegs,
                unsigned _numPhysicalVecRegs,
                unsigned _numPhysicalVecPredRegs,
                unsigned _numPhysicalMatRegs,
                unsigned _numPhysicalCCRegs,
                const BaseISA::RegClasses &classes);

    /**
     * Destructor to free resources
     */
    ~PhysRegFile() {}

    /** Initialize the free list */
    void initFreeList(UnifiedFreeList *freeList);

    /** @return the total number of physical registers. */
    unsigned totalNumPhysRegs() const { return totalNumRegs; }

    /** Gets a misc register PhysRegIdPtr. */
    PhysRegIdPtr getMiscRegId(RegIndex reg_idx) {
        return &miscRegIds[reg_idx];
    }

    RegVal
    getReg(PhysRegIdPtr phys_reg) const
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        RegVal val;
        switch (type) {
          case IntRegClass:
            val = intRegFile.reg(idx);
            DPRINTF(IEW, "RegFile: Access to int register %i, has data %#x\n",
                    idx, val);
            return val;
          case FloatRegClass:
            val = floatRegFile.reg(idx);
            DPRINTF(IEW, "RegFile: Access to float register %i has data %#x\n",
                    idx, val);
            return val;
          case VecElemClass:
            val = vectorElemRegFile.reg(idx);
            DPRINTF(IEW, "RegFile: Access to vector element register %i "
                    "has data %#x\n", idx, val);
            return val;
          case CCRegClass:
            val = ccRegFile.reg(idx);
            DPRINTF(IEW, "RegFile: Access to cc register %i has data %#x\n",
                    idx, val);
            return val;
          default:
            panic("Unsupported register class type %d.", type);
        }
    }

    void
    getReg(PhysRegIdPtr phys_reg, void *val) const
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        switch (type) {
          case IntRegClass:
            *(RegVal *)val = getReg(phys_reg);
            break;
          case FloatRegClass:
            *(RegVal *)val = getReg(phys_reg);
            break;
          case VecRegClass:
            vectorRegFile.get(idx, val);
            DPRINTF(IEW, "RegFile: Access to vector register %i, has "
                    "data %s\n", idx, vectorRegFile.regClass.valString(val));
            break;
          case VecElemClass:
            *(RegVal *)val = getReg(phys_reg);
            break;
          case VecPredRegClass:
            vecPredRegFile.get(idx, val);
            DPRINTF(IEW, "RegFile: Access to predicate register %i, has "
                    "data %s\n", idx, vecPredRegFile.regClass.valString(val));
            break;
          case MatRegClass:
            matRegFile.get(idx, val);
            DPRINTF(IEW, "RegFile: Access to matrix register %i, has "
                    "data %s\n", idx, matRegFile.regClass.valString(val));
            break;
          case CCRegClass:
            *(RegVal *)val = getReg(phys_reg);
            break;
          default:
            panic("Unrecognized register class type %d.", type);
        }
    }

    void *
    getWritableReg(PhysRegIdPtr phys_reg)
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        switch (type) {
          case VecRegClass:
            return vectorRegFile.ptr(idx);
          case VecPredRegClass:
            return vecPredRegFile.ptr(idx);
          case MatRegClass:
            return matRegFile.ptr(idx);
          default:
            panic("Unrecognized register class type %d.", type);
        }
    }

    void
    setReg(PhysRegIdPtr phys_reg, RegVal val)
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        switch (type) {
          case InvalidRegClass:
            break;
          case IntRegClass:
            intRegFile.reg(idx) = val;
            DPRINTF(IEW, "RegFile: Setting int register %i to %#x\n",
                    idx, val);
            break;
          case FloatRegClass:
            floatRegFile.reg(idx) = val;
            DPRINTF(IEW, "RegFile: Setting float register %i to %#x\n",
                    idx, val);
            break;
          case VecElemClass:
            vectorElemRegFile.reg(idx) = val;
            DPRINTF(IEW, "RegFile: Setting vector element register %i to "
                    "%#x\n", idx, val);
            break;
          case CCRegClass:
            ccRegFile.reg(idx) = val;
            DPRINTF(IEW, "RegFile: Setting cc register %i to %#x\n",
                    idx, val);
            break;
          default:
            panic("Unsupported register class type %d.", type);
        }
    }

    void
    setReg(PhysRegIdPtr phys_reg, const void *val)
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        switch (type) {
          case IntRegClass:
            setReg(phys_reg, *(RegVal *)val);
            break;
          case FloatRegClass:
            setReg(phys_reg, *(RegVal *)val);
            break;
          case VecRegClass:
            DPRINTF(IEW, "RegFile: Setting vector register %i to %s\n",
                    idx, vectorRegFile.regClass.valString(val));
            vectorRegFile.set(idx, val);
            break;
          case VecElemClass:
            setReg(phys_reg, *(RegVal *)val);
            break;
          case VecPredRegClass:
            DPRINTF(IEW, "RegFile: Setting predicate register %i to %s\n",
                    idx, vecPredRegFile.regClass.valString(val));
            vecPredRegFile.set(idx, val);
            break;
          case MatRegClass:
            DPRINTF(IEW, "RegFile: Setting matrix register %i to %s\n",
                    idx, matRegFile.regClass.valString(val));
            matRegFile.set(idx, val);
            break;
          case CCRegClass:
            setReg(phys_reg, *(RegVal *)val);
            break;
          default:
            panic("Unrecognized register class type %d.", type);
        }
    }



    bool
    getTaint(PhysRegIdPtr phys_reg) const
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();
        bool val;
        switch (type) {
            case IntRegClass:
                val = intRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to int "
                             "register %i, has taint %#x\n",
                        idx, val);
                return val;
            case FloatRegClass:
                val = floatRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to float "
                             "register %i has taint %#x\n",
                        idx, val);
                return val;
            case VecElemClass:
                val = vecElemRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to vector element "
                             "register %i "
                             "has taint %#x\n", idx, val);
                return val;
            case CCRegClass:
                val = ccRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to cc "
                             "register %i has taint %#x\n",
                        idx, val);
                return val;
            case VecPredRegClass:
                val = vecPredTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to VecPredRegClass "
                             "register %i has taint %#x\n",
                        idx, val);
                return val;
            case VecRegClass:
                val = vectorRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has taint %#x\n",
                        idx, val);
                return val;
            case MiscRegClass:
                val = miscRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to Misc "
                             "register %i has taint %#x\n",
                        idx, val);
                return val;
            case MatRegClass:
                val = matRegTaints.at(idx);
                DPRINTF(IEW, "RegFile: Access to MatRegClass "
                             "register %i has taint %#x\n",
                        idx, val);
                return val;
            default:
                DPRINTF(IEW,"Unsupported register class type %d.", type);
                return false;
        }
    }

    InstSeqNum
    getYRoT(PhysRegIdPtr phys_reg) const
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        InstSeqNum val;
        switch (type) {
            case IntRegClass:
                val = intRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to int "
                             "register %i, has YRoT %#x\n",
                        idx, val);
                return val;
            case FloatRegClass:
                val = floatRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to float "
                             "register %i has YRoT %#x\n",
                        idx, val);
                return val;
            case VecElemClass:
                val = vecElemRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to vector element"
                             " register %i "
                             "has YRoT %#x\n", idx, val);
                return val;
            case CCRegClass:
                val = ccRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to cc "
                             "register %i has YRoT %#x\n",
                        idx, val);
                return val;
            case VecPredRegClass:
                val = vecPredRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to VecPredRegClass "
                             "register %i has YRoT %#x\n",
                        idx, val);
                return val;
            case VecRegClass:
                val = vectorRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has YRoT %#x\n",
                        idx, val);
                return val;
            case MiscRegClass:
                val = miscRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has YRoT %#x\n",
                        idx, val);
                return val;
            case MatRegClass:
                val = matRegYRoTs.at(idx);
                DPRINTF(IEW, "RegFile: Access to MatRegClass "
                             "register %i has YRoT %#x\n",
                        idx, val);
                return val;
            default:
                DPRINTF(IEW,"Unsupported register class type %d.", type);
                return 0;
        }
    }

    void
    setYRoT(PhysRegIdPtr phys_reg, InstSeqNum yRoT)
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        switch (type) {
            case IntRegClass:
                intRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Set YRoT of int "
                             "register %i, as %#x\n",
                        idx, yRoT);
                return;
            case FloatRegClass:
                floatRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Set YRoT of float "
                             "register %i as %#x\n",
                        idx, yRoT);
                return;
            case VecElemClass:
                vecElemRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Set YRoT of vector element "
                             "register %i "
                             "as %#x\n", idx, yRoT);
                return;
            case CCRegClass:
                ccRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Set YRoT of cc "
                             "register %i as %#x\n",
                        idx, yRoT);
                return;
            case VecPredRegClass:
                vecPredRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Access to VecPredRegClass "
                             "register %i has YRoT %#x\n",
                        idx, yRoT);
                return;
            case VecRegClass:
                vectorRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has YRoT %#x\n",
                        idx, yRoT);
                return;
            case MiscRegClass:
                miscRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has YRoT %#x\n",
                        idx, yRoT);
                return;
            case MatRegClass:
                matRegYRoTs.at(idx) = yRoT;
                DPRINTF(IEW, "RegFile: Access to MatRegClass "
                             "register %i has taint %#x\n",
                        idx, yRoT);
                return;
            default:
                DPRINTF(IEW,"Unsupported register class type %d.", type);
                return;
        }
    }

    void
    setTaint(PhysRegIdPtr phys_reg, bool taint)
    {
        const RegClassType type = phys_reg->classValue();
        const RegIndex idx = phys_reg->index();

        switch (type) {
            case IntRegClass:
                intRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Set taint of int "
                             "register %i, as %#x\n",
                        idx, taint);
                return;
            case FloatRegClass:
                floatRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Set taint of float "
                             "register %i as %#x\n",
                        idx, taint);
                return;
            case VecElemClass:
                vecElemRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Set taint of vector element "
                             "register %i "
                             "as %#x\n", idx, taint);
                return;
            case CCRegClass:
                ccRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Set taint of cc "
                             "register %i as %#x\n",
                        idx, taint);
                return;
            case VecPredRegClass:
                vecPredTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Access to VecPredRegClass "
                             "register %i has taint %#x\n",
                        idx, taint);
                return;
            case VecRegClass:
                vectorRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has taint %#x\n",
                        idx, taint);
                return;
            case MiscRegClass:
                miscRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Access to VecRegClass "
                             "register %i has taint %#x\n",
                        idx, taint);
                return;
            case MatRegClass:
                matRegTaints.at(idx) = taint;
                DPRINTF(IEW, "RegFile: Access to MatRegClass "
                             "register %i has taint %#x\n",
                        idx, taint);
                return;
            default:
                DPRINTF(IEW,"Unsupported register class type %d.", type);
                return;
        }
    }

    void
    clearYRoTsAndTaints(const std::vector<InstSeqNum>& yRoTs)
    {

        //TODO optimize for runtime
        for (const auto& yRoT: yRoTs) {
            int i = 0;
            for (const auto& iYRT: intRegYRoTs) {
                if (iYRT == yRoT) {
                    intRegYRoTs.at(i) = 0;
                    intRegTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: floatRegYRoTs) {
                if (iYRT == yRoT) {
                    floatRegYRoTs.at(i) = 0;
                    floatRegTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: vectorRegYRoTs) {
                if (iYRT == yRoT) {
                    vectorRegYRoTs.at(i) = 0;
                    vectorRegTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: vecElemRegYRoTs) {
                if (iYRT == yRoT) {
                    vecElemRegYRoTs.at(i) = 0;
                    vecElemRegTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: vecPredRegYRoTs) {
                if (iYRT == yRoT) {
                    vecPredRegYRoTs.at(i) = 0;
                    vecPredTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: ccRegYRoTs) {
                if (iYRT == yRoT) {
                    ccRegYRoTs.at(i) = 0;
                    ccRegTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: miscRegYRoTs) {
                if (iYRT == yRoT) {
                    miscRegYRoTs.at(i) = 0;
                    miscRegTaints.at(i) = false;
                }
                i++;
            }
            i = 0;
            for (const auto& iYRT: matRegYRoTs) {
                if (iYRT == yRoT) {
                    matRegYRoTs.at(i) = 0;
                    matRegTaints.at(i) = false;
                }
                i++;
            }
        }
    }
};

} // namespace o3
} // namespace gem5

#endif //__CPU_O3_REGFILE_HH__
