#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "../hw/pihash.h"

namespace py = pybind11;
using namespace pisecure::pihash;

/**
 * PiHash Python Bindings
 * 
 * SECURITY NOTE: These bindings are intentionally minimal and do NOT expose
 * the hardware verification implementation details. Users interact with
 * opaque functions, while the actual verification logic remains sealed
 * within the compiled C++ binary.
 */

PYBIND11_MODULE(pisecure_cpp_pihash, m) {
    m.doc() = "PiHash mining algorithm (C++ compiled, hardware-verified)";
    
    // HardwareFingerprint struct (read-only from Python perspective)
    py::class_<HardwareFingerprint>(m, "HardwareFingerprint")
        .def_readwrite("cpu_serial", &HardwareFingerprint::cpu_serial)
        .def_readwrite("hardware_model", &HardwareFingerprint::hardware_model)
        .def_readwrite("mac_address", &HardwareFingerprint::mac_address)
        .def_readwrite("memory_total", &HardwareFingerprint::memory_total)
        .def_readwrite("hardware_rng", &HardwareFingerprint::hardware_rng)
        .def_readwrite("unique_id", &HardwareFingerprint::unique_id)
        .def_readwrite("timestamp", &HardwareFingerprint::timestamp);
    
    // Main PiHash class
    py::class_<PiHash>(m, "PiHash")
        .def(py::init<int, int, bool>(),
             py::arg("rounds") = 1,
             py::arg("memory_mb") = 1,
             py::arg("npu_enabled") = false)
        
        // Core mining functions
        .def("compute",
             &PiHash::Compute,
             py::arg("data"),
             py::arg("nonce"),
             py::arg("fingerprint") = nullptr,
             "Compute PiHash for given data and nonce. Hardware verification is performed internally.")
        
        .def("find_nonce",
             &PiHash::FindNonce,
             py::arg("block_data"),
             py::arg("difficulty"),
             py::arg("fingerprint") = nullptr,
             py::arg("max_attempts") = 0xFFFFFFFF,
             "Find nonce meeting difficulty requirement. Mining loop runs in optimized C++.")
        
        .def_static("meets_difficulty",
                    &PiHash::MeetsDifficulty,
                    py::arg("hash_hex"),
                    py::arg("target_zero_bits"),
                    "Check if hash meets zero-bit difficulty")
        
        // Hardware interface (minimal exposure)
        .def_static("get_hardware_fingerprint",
                    &PiHash::GetHardwareFingerprint,
                    "Get current system hardware fingerprint. Implementation details are sealed in binary.")
        
        .def_static("verify_hardware",
                    &PiHash::VerifyHardware,
                    py::arg("fingerprint"),
                    "Verify hardware is genuine Raspberry Pi. Verification algorithm is sealed in binary.");
    
    // Module-level convenience functions
    m.def("compute_pihash",
          &ComputePiHash,
          py::arg("data"),
          py::arg("nonce") = 0,
          py::arg("rounds") = 8,
          py::arg("memory_mb") = 256,
          "Convenience function to compute PiHash");
    
    m.def("mine_block",
          &MineBlock,
          py::arg("block_data"),
          py::arg("difficulty"),
          py::arg("max_attempts") = 0xFFFFFFFF,
          "Mine block by finding valid nonce. Mining loop optimized in C++.");
}
