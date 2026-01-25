/**
 * bindings/pybind_hw_verifier.cpp - Python bindings for hardware verification
 */
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "../hw/hw_verifier.h"

namespace py = pybind11;
using namespace pisecure::hw;

PYBIND11_MODULE(pisecure_cpp_hw, m) {
    m.doc() = "PiSecure hardware verification (C++ core)";

    // PiModel enum
    py::enum_<PiModel>(m, "PiModel")
        .value("UNKNOWN", PiModel::UNKNOWN)
        .value("PI_ZERO", PiModel::PI_ZERO)
        .value("PI_ZERO_W", PiModel::PI_ZERO_W)
        .value("PI_ZERO_2W", PiModel::PI_ZERO_2W)
        .value("PI_1_A", PiModel::PI_1_A)
        .value("PI_1_B", PiModel::PI_1_B)
        .value("PI_1_A_PLUS", PiModel::PI_1_A_PLUS)
        .value("PI_1_B_PLUS", PiModel::PI_1_B_PLUS)
        .value("PI_2_B", PiModel::PI_2_B)
        .value("PI_3_B", PiModel::PI_3_B)
        .value("PI_3_B_PLUS", PiModel::PI_3_B_PLUS)
        .value("PI_3_A_PLUS", PiModel::PI_3_A_PLUS)
        .value("PI_4_B", PiModel::PI_4_B)
        .value("PI_400", PiModel::PI_400)
        .value("PI_CM4", PiModel::PI_CM4)
        .value("PI_5", PiModel::PI_5)
        .value("PI_CM5", PiModel::PI_CM5)
        .value("NOT_PI", PiModel::NOT_PI)
        .export_values();

    // HardwareInfo struct
    py::class_<HardwareInfo>(m, "HardwareInfo")
        .def(py::init<>())
        .def_readwrite("is_genuine_pi", &HardwareInfo::is_genuine_pi)
        .def_readwrite("model", &HardwareInfo::model)
        .def_readwrite("cpu_serial", &HardwareInfo::cpu_serial)
        .def_readwrite("board_revision", &HardwareInfo::board_revision)
        .def_readwrite("soc_id", &HardwareInfo::soc_id)
        .def_readwrite("has_hwrng", &HardwareInfo::has_hwrng)
        .def_readwrite("virtualized", &HardwareInfo::virtualized)
        .def_readwrite("error_message", &HardwareInfo::error_message)
        .def("__repr__", [](const HardwareInfo& info) {
            return "<HardwareInfo genuine=" + std::string(info.is_genuine_pi ? "True" : "False") +
                   " model=" + HardwareVerifier::model_name(info.model) +
                   " serial=" + info.cpu_serial + ">";
        });

    // EntropyQuality struct
    py::class_<EntropyQuality>(m, "EntropyQuality")
        .def(py::init<>())
        .def_readwrite("sufficient", &EntropyQuality::sufficient)
        .def_readwrite("bits_per_byte", &EntropyQuality::bits_per_byte)
        .def_readwrite("sample_size", &EntropyQuality::sample_size)
        .def_readwrite("chi_square", &EntropyQuality::chi_square)
        .def_readwrite("uniformity_ok", &EntropyQuality::uniformity_ok)
        .def_readwrite("failure_reason", &EntropyQuality::failure_reason)
        .def("__repr__", [](const EntropyQuality& q) {
            return "<EntropyQuality sufficient=" + std::string(q.sufficient ? "True" : "False") +
                   " bits/byte=" + std::to_string(q.bits_per_byte) +
                   " chi_square=" + std::to_string(q.chi_square) + ">";
        });

    // HardwareVerifier class
    py::class_<HardwareVerifier>(m, "HardwareVerifier")
        .def(py::init<>())
        .def("verify_hardware", &HardwareVerifier::verify_hardware,
             "Perform comprehensive hardware verification")
        .def("read_entropy", &HardwareVerifier::read_entropy,
             "Read entropy from /dev/hwrng and assess quality",
             py::arg("num_bytes") = 32, py::arg("timeout_ms") = 1000)
        .def("get_cpu_serial", &HardwareVerifier::get_cpu_serial,
             "Get CPU serial from /proc/cpuinfo")
        .def("get_board_revision", &HardwareVerifier::get_board_revision,
             "Get board revision from /proc/cpuinfo")
        .def("detect_pi_model", &HardwareVerifier::detect_pi_model,
             "Detect Pi model from revision code",
             py::arg("revision"))
        .def("detect_virtualization", &HardwareVerifier::detect_virtualization,
             "Check if running in virtualized environment")
        .def("is_mining_capable", &HardwareVerifier::is_mining_capable,
             "Validate hardware fingerprint for mining");

    // Static functions
    m.def("model_name", &HardwareVerifier::model_name,
          "Get human-readable model name",
          py::arg("model"));

    m.def("hw_selftest", &HardwareVerifier::selftest,
          "Run hardware verifier self-test");
}
