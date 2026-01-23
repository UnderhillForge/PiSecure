/**
 * pybind_consensus.cpp - Python bindings for consensus math
 */
#include <pybind11/pybind11.h>
#include <pybind11/operators.h>
#include "../consensus/uint256.h"
#include "../consensus/arith_uint256.h"

namespace py = pybind11;
using namespace pisecure::consensus;

PYBIND11_MODULE(pisecure_cpp_consensus, m) {
    m.doc() = "PiSecure C++ consensus module (256-bit arithmetic, PoW)";
    
    // Blob256 - opaque hash container
    py::class_<Blob256>(m, "Blob256")
        .def_static("from_bytes", [](py::bytes data) {
            const char* ptr = PyBytes_AsString(data.ptr());
            if (!ptr) throw std::runtime_error("Failed to read bytes");
            if (PyBytes_Size(data.ptr()) != 32) {
                throw std::runtime_error("Data must be 32 bytes");
            }
            return Blob256::from_bytes(reinterpret_cast<const uint8_t*>(ptr));
        }, "Create from 32-byte array")
        .def_static("from_hex", &Blob256::from_hex, "Create from hex string (64 chars)")
        .def("to_bytes", [](const Blob256& self) {
            uint8_t out[32];
            self.to_bytes(out);
            return py::bytes(reinterpret_cast<const char*>(out), 32);
        }, "Output as 32-byte array")
        .def("to_hex", &Blob256::to_hex, "Convert to hex string")
        .def("is_zero", &Blob256::is_zero, "Check if all zeros")
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def(py::self < py::self)
        .def(py::self <= py::self)
        .def(py::self > py::self)
        .def(py::self >= py::self);
    
    // Big256 - 256-bit integer for consensus math
    py::class_<Big256>(m, "Big256")
        .def(py::init<>())
        .def(py::init<uint64_t>())
        .def_static("from_bytes", [](py::bytes data) {
            const char* ptr = PyBytes_AsString(data.ptr());
            if (!ptr) throw std::runtime_error("Failed to read bytes");
            if (PyBytes_Size(data.ptr()) != 32) {
                throw std::runtime_error("Data must be 32 bytes");
            }
            return Big256::from_bytes(reinterpret_cast<const uint8_t*>(ptr));
        }, "Create from 32-byte little-endian")
        .def_static("from_compact", [](uint32_t nbits) {
            bool neg, overflow;
            Big256 result = Big256::from_compact(nbits, neg, overflow);
            return py::make_tuple(result, neg, overflow);
        }, "Create from compact difficulty (Bitcoin-style)")
        .def("to_bytes", [](const Big256& self) {
            uint8_t out[32];
            self.to_bytes(out);
            return py::bytes(reinterpret_cast<const char*>(out), 32);
        }, "Output as 32-byte little-endian")
        .def("get_compact", &Big256::get_compact, "Convert to compact representation")
        .def("is_zero", &Big256::is_zero)
        .def("is_negative", &Big256::is_negative)
        .def("leading_zero_bits", &Big256::leading_zero_bits, "Count leading zeros (MSB)")
        .def("bits", &Big256::bits, "Count total bits")
        .def("set_zero", &Big256::set_zero)
        .def(py::self += py::self)
        .def(py::self -= py::self)
        .def(py::self == py::self)
        .def(py::self != py::self)
        .def(py::self < py::self)
        .def(py::self <= py::self)
        .def(py::self > py::self)
        .def(py::self >= py::self);
    
    m.def("ct_equal", &ct_equal, "Constant-time equality check");
    m.def("ct_less_or_equal", &ct_less_or_equal, "Constant-time less-or-equal check");
}
