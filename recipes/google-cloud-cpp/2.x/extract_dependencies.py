#!/usr/bin/env python3

import argparse
import glob
import os

"""Extract google-cloud-cpp's component dependency info for use in Conan.

google-cloud-cpp builds a number (about 100) of libraries from proto files.
These libraries have dependencies between them. In Conan, one cannot use the
dependencies preserved in the *-config.cmake files generated by the package, so
we have to reconstruct the dependencies here.

Fortunately, google-cloud-cpp uses a number of *.deps files to keep these
dependencies. We just need to reimplement their algorithm to load these files
and convert them to CMake dependencies.

The *.deps files themselves are generated (and committed to GitHub) from
Bazel rules.
"""

# Used in _generate_proto_requires(): common requirements
_PROTO_DEPS_COMMON_REQUIRES = {"grpc::grpc++", "grpc::_grpc", "protobuf::libprotobuf"}

# Used in _generate_proto_requires(): the *.deps files are generated from
# Bazel and contain a few targets that do not exit (nor do they need to
# exist) in CMake.
_PROTO_DEPS_REMOVED_TARGETS = {
    "cloud_kms_v1_kms_protos",
    "cloud_orgpolicy_v1_orgpolicy_protos",
    "cloud_oslogin_common_common_protos",
    "cloud_recommender_v1_recommender_protos",
    "identity_accesscontextmanager_type_type_protos",
}

# Used in _generate_proto_requires(): the *.deps files are generated from
# Bazel and contain a few targets that have incorrect names for CMake.
_PROTO_DEPS_REPLACED_TARGETS = {
    "grafeas_v1_grafeas_protos": "grafeas_protos",
    "identity_accesscontextmanager_v1_accesscontextmanager_protos": "accesscontextmanager_protos",
    "cloud_osconfig_v1_osconfig_protos": "osconfig_protos",
    "devtools_source_v1_source_protos": "devtools_source_v1_source_context_protos",
    "cloud_documentai_v1_documentai_protos": "documentai_protos",
}

# A few *.deps files use ad-hoc naming.
_PROTO_DEPS_REPLACED_NAMES = {
    "common": "cloud_common_common",
    "bigquery": "cloud_bigquery",
    "dialogflow": "cloud_dialogflow_v2",
    "logging_type": "logging_type_type",
    "texttospeech": "cloud_texttospeech",
    "speech": "cloud_speech",
    "trace": "devtools_cloudtrace_v2_trace",
}

# A few *.deps files are not used.
_PROTO_DEPS_UNUSED = {
    "iam_policy",
}

# A few _protos libraries were introduced before `google-cloud-cpp` adopted
# more consistent naming.
_PROTO_BASE_COMPONENTS = {
    "api_service_protos",
    "api_visibility_protos",
    "api_monitoring_protos",
    "type_date_protos",
    "api_control_protos",
    "api_client_protos",
    "api_annotations_protos",
    "api_httpbody_protos",
    "iam_v1_policy_protos",
    "api_auth_protos",
    "api_resource_protos",
    "api_billing_protos",
    "api_quota_protos",
    "api_source_info_protos",
    "api_backend_protos",
    "type_datetime_protos",
    "iam_v1_options_protos",
    "api_endpoint_protos",
    "api_launch_stage_protos",
    "api_documentation_protos",
    "devtools_source_v1_source_context_protos",
    "type_color_protos",
    "api_distribution_protos",
    "api_config_change_protos",
    "iam_v1_iam_policy_protos",
    "type_expr_protos",
    "api_routing_protos",
    "api_usage_protos",
    "logging_type_type_protos",
    "type_calendar_period_protos",
    "rpc_code_protos",
    "api_system_parameter_protos",
    "cloud_common_common_protos",
    "type_postal_address_protos",
    "type_latlng_protos",
    "type_dayofweek_protos",
    "api_monitored_resource_protos",
    "type_money_protos",
    "api_metric_protos",
    "api_label_protos",
    "api_log_protos",
    "grafeas_protos",
    "api_http_protos",
    "type_timeofday_protos",
    "api_field_behavior_protos",
    "api_context_protos",
    "api_logging_protos",
}

# A list of experimental components used when `google-cloud-cpp` does not
# provide an easy-to-use list.
_DEFAULT_EXPERIMENTAL_COMPONENTS = {
    "apikeys",
    "pubsublite",
}

# A list of components used when `google-cloud-cpp` does not provide an
# easy-to-use list.
_DEFAULT_COMPONENTS = {
    "accessapproval",
    "accesscontextmanager",
    "apigateway",
    "apigeeconnect",
    "appengine",
    "artifactregistry",
    "asset",
    "assuredworkloads",
    "automl",
    "baremetalsolution",
    "batch",
    "beyondcorp",
    "bigquery",
    "bigtable",
    "billing",
    "binaryauthorization",
    "certificatemanager",
    "channel",
    "cloudbuild",
    "composer",
    "connectors",
    "contactcenterinsights",
    "container",
    "containeranalysis",
    "datacatalog",
    "datamigration",
    "dataplex",
    "dataproc",
    "datastream",
    "debugger",
    "deploy",
    "dialogflow_cx",
    "dialogflow_es",
    "dlp",
    "documentai",
    "edgecontainer",
    "eventarc",
    "filestore",
    "functions",
    "gameservices",
    "gkehub",
    "iam",
    "iap",
    "ids",
    "iot",
    "kms",
    "language",
    "logging",
    "managedidentities",
    "memcache",
    "monitoring",
    "networkconnectivity",
    "networkmanagement",
    "notebooks",
    "optimization",
    "orgpolicy",
    "osconfig",
    "oslogin",
    "policytroubleshooter",
    "privateca",
    "profiler",
    "pubsub",
    "recommender",
    "redis",
    "resourcemanager",
    "resourcesettings",
    "retail",
    "run",
    "scheduler",
    "secretmanager",
    "securitycenter",
    "servicecontrol",
    "servicedirectory",
    "servicemanagement",
    "serviceusage",
    "shell",
    "spanner",
    "speech",
    "storage",
    "storagetransfer",
    "talent",
    "tasks",
    "texttospeech",
    "tpu",
    "trace",
    "translate",
    "video",
    "videointelligence",
    "vision",
    "vmmigration",
    "vmwareengine",
    "vpcaccess",
    "webrisk",
    "websecurityscanner",
    "workflows",
}

# `google-cloud-cpp` manages these dependencies using CMake code.
_HARD_CODED_DEPENDENCIES = {
    "api_annotations_protos": ["api_http_protos"],
    "api_auth_protos": ["api_annotations_protos"],
    "api_client_protos": ["api_launch_stage_protos"],
    "api_metric_protos": ["api_launch_stage_protos", "api_label_protos"],
    "api_billing_protos": ["api_annotations_protos", "api_metric_protos"],
    "api_distribution_protos": ["api_annotations_protos"],
    "api_endpoint_protos": ["api_annotations_protos"],
    "api_log_protos": ["api_label_protos"],
    "api_logging_protos": ["api_annotations_protos", "api_label_protos"],
    "api_monitored_resource_protos": ["api_launch_stage_protos", "api_label_protos"],
    "api_monitoring_protos": ["api_annotations_protos"],
    "api_quota_protos": ["api_annotations_protos"],
    "api_usage_protos": ["api_annotations_protos", "api_visibility_protos"],
    "api_service_protos": [
        "api_annotations_protos",
        "api_auth_protos",
        "api_backend_protos",
        "api_billing_protos",
        "api_client_protos",
        "api_context_protos",
        "api_control_protos",
        "api_documentation_protos",
        "api_endpoint_protos",
        "api_http_protos",
        "api_label_protos",
        "api_log_protos",
        "api_logging_protos",
        "api_metric_protos",
        "api_monitored_resource_protos",
        "api_monitoring_protos",
        "api_quota_protos",
        "api_resource_protos",
        "api_source_info_protos",
        "api_system_parameter_protos",
        "api_usage_protos",
    ],
    "devtools_cloudtrace_v2_tracing_protos": [
        "devtools_cloudtrace_v2_trace_protos",
        "devtools_cloudtrace_v2_trace_protos",
        "api_client_protos",
        "api_field_behavior_protos",
        "rpc_status_protos",
    ],
}


def _components(source_folder):
    libraries = os.path.join(source_folder, "libraries.bzl")
    # Use the hard-coded list because the `google-cloud-cpp` does not provide
    # an easy way to get all the components.
    if not os.path.exists(libraries):
        return _DEFAULT_COMPONENTS
    # The `libraries.bzl` file is a Starlark file that simply defines some
    # variables listing all GA, experimental, and "transition", components.
    # We want both the GA and transition components, the latter are components
    # that recently transitioned from experimental to GA.
    g = dict()
    with open(libraries) as f:
        exec(compile(f.read(), libraries, "exec"), g)
    return (
        g["GOOGLE_CLOUD_CPP_GA_LIBRARIES"] + g["GOOGLE_CLOUD_CPP_TRANSITION_LIBRARIES"]
    )


def _experimental_components(source_folder):
    libraries = os.path.join(source_folder, "libraries.bzl")
    # Use the hard-coded list because the `google-cloud-cpp` does not provide
    # an easy way to get all the components.
    if not os.path.exists(libraries):
        return _DEFAULT_EXPERIMENTAL_COMPONENTS
    # The `libraries.bzl` file is a Starlark file that simply defines some
    # variables listing all GA, experimental, and "transition", components.
    # We want to return any experimental components, the caller will skip them
    # as they are not built by Conan.
    g = dict()
    with open(libraries) as f:
        exec(compile(f.read(), libraries, "exec"), g)
    return g["GOOGLE_CLOUD_CPP_EXPERIMENTAL_LIBRARIES"]


def _generate_proto_requires(depfile):
    """Load the dependencies for a single google-cloud-cpp::*-protos library."""
    requires = []
    with open(depfile, "r", encoding="utf-8") as f:
        for line in f.readlines():
            line = line.strip()
            line = line.replace(":", "_")
            line = line.replace("_proto", "_protos")
            line = line.replace("@com_google_googleapis//", "")
            line = line.replace("google/", "")
            line = line.replace("/", "_")
            if line in _PROTO_DEPS_REMOVED_TARGETS:
                continue
            line = _PROTO_DEPS_REPLACED_TARGETS.get(line, line)
            requires.append(line)
    return list(_PROTO_DEPS_COMMON_REQUIRES) + requires


def main():
    """Generate a python file representing the google-cloud-cpp proto deps."""
    parser = argparse.ArgumentParser(description=(__doc__))
    parser.add_argument(
        "-s",
        "--source-folder",
        help="a directory where `google-cloud-cpp` source has been extracted",
    )
    args = parser.parse_args()
    source_folder = vars(args)["source_folder"]
    deps_folder = os.path.join(source_folder, "external", "googleapis", "protodeps")
    print("# Automatically generated by %s DO NOT EDIT" % __file__)
    print("DEPENDENCIES = {")
    proto_components = _PROTO_BASE_COMPONENTS.copy()
    files = sorted(glob.glob(os.path.join(deps_folder, "*.deps")))
    experimental = set(_experimental_components(source_folder))
    for filename in files:
        component = os.path.basename(filename).replace(".deps", "")
        component = _PROTO_DEPS_REPLACED_NAMES.get(component, component)
        if component in experimental or component in _PROTO_DEPS_UNUSED:
            # Experimental components have an associated *_protos, component.
            # The Conan package only compiles the GA components, so we need
            # to skip these.
            continue
        component = component + "_protos"
        deps = _generate_proto_requires(filename)
        proto_components.add(component)
        proto_components.update(deps)
        print(f'    "{component}": {sorted(deps)},')
    for component in sorted(_HARD_CODED_DEPENDENCIES.keys()):
        deps = _HARD_CODED_DEPENDENCIES[component]
        proto_components.add(component)
        proto_components.update(deps)
        print(f'    "{component}": {sorted(deps)},')
    print("}")
    proto_components = proto_components - _PROTO_DEPS_COMMON_REQUIRES
    names = ['"%s"' % c for c in proto_components]
    joined = ",\n    ".join(sorted(names))
    print(f"\nPROTO_COMPONENTS = {{\n    {joined}\n}}")
    names = ['"%s"' % c for c in _components(source_folder)]
    joined = ",\n    ".join(sorted(names))
    print(f"\nCOMPONENTS = {{\n    {joined}\n}}")


if __name__ == "__main__":
    main()
