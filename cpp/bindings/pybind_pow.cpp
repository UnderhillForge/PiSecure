/**
 * bindings/pybind_pow.cpp - Python bindings for PoW consensus
 */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "../consensus/pow.h"
#include "../consensus/uint256.h"
#include "../consensus/arith_uint256.h"

namespace py = pybind11;
using namespace pisecure::consensus;

PYBIND11_MODULE(pisecure_cpp_pow, m) {
    m.doc() = "PiSecure PoW consensus logic (C++ core)";
    
    // DifficultyParams struct
    py::class_<DifficultyParams>(m, "DifficultyParams")
        .def(py::init<>())
        .def_readwrite("retarget_time_target", &DifficultyParams::retarget_time_target)
        .def_readwrite("max_adjustment_factor", &DifficultyParams::max_adjustment_factor)
        .def("__repr__", [](const DifficultyParams& p) {
            return "<DifficultyParams time_target=" + 
                   std::to_string(p.retarget_time_target) + 
                   " max_adjustment=" + std::to_string(p.max_adjustment_factor) + ">";
        });
    
    // CompactDecoded struct
    py::class_<CompactDecoded>(m, "CompactDecoded")
        .def(py::init<>())
        .def_readwrite("target", &CompactDecoded::target)
        .def_readwrite("negative", &CompactDecoded::negative)
        .def_readwrite("overflow", &CompactDecoded::overflow)
        .def("__repr__", [](const CompactDecoded& c) {
            return "<CompactDecoded target=" + c.target.to_hex() + 
                   " negative=" + std::string(c.negative ? "true" : "false") + 
                   " overflow=" + std::string(c.overflow ? "true" : "false") + ">";
        });
    
    // PoW functions
    m.def("leading_zeros_to_target", &leading_zeros_to_target,
          "Convert leading zero bits to target Big256",
          py::arg("leading_zero_bits"));
    
    m.def("target_to_leading_zeros", &target_to_leading_zeros,
          "Convert target Big256 to leading zero bits count",
          py::arg("target"));
    
    m.def("check_pow", &check_pow,
          "Constant-time PoW check: hash <= target",
          py::arg("hash"), py::arg("target"));
    
    m.def("check_pow_leading_zeros", &check_pow_leading_zeros,
          "Check if hash has required leading zeros",
          py::arg("hash"), py::arg("required_leading_zeros"));
    
    m.def("calculate_next_target", &calculate_next_target,
          "Calculate next difficulty target (adaptive retarget)",
          py::arg("last_target"), py::arg("actual_time"), 
          py::arg("params") = DifficultyParams());
    
    m.def("encode_compact", &encode_compact,
          "Encode Big256 target to Bitcoin-style compact representation",
          py::arg("target"));
    
    m.def("decode_compact", &decode_compact,
          "Decode Bitcoin-style compact representation to target",
          py::arg("nbits"));
    
    m.def("get_pow_limit", &get_pow_limit,
          "Get the maximum PoW target (minimum difficulty)");
    
    m.def("is_valid_target", &is_valid_target,
          "Check if target is valid within pow_limit",
          py::arg("target"), py::arg("pow_limit"));
    
    m.def("pow_selftest", &pow_selftest,
          "Run self-tests for PoW functions");
}
