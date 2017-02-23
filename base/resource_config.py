hosts_data = {
    "jpol": {
        "G0_mb-inrpc": [
                           {"hostname": "10.99.70.75"},
                       ],
        # "G1_node-api": [
        #                    {"hostname": "10.99.70.58"},
        #                ],
        # "G2_node-api": [
        #                    {"hostname": "10.99.70.59"},
        #                ],
        # "G1_mb-inrpc": [
        #                    {"hostname": "10.99.70.60"},
        #                ],
        # "G2_mb-inrpc": [
        #                    {"hostname": "10.99.70.61"},
        #                ],
        # "G1_planner-inrpc": [
        #                    {"hostname": "10.99.70.62"},
        #                ],
        # "G2_planner-inrpc": [
        #                    {"hostname": "10.99.70.63"},
        #                ],
        # "G1_msg2-inrpc": [
        #                    {"hostname": "10.99.70.64"},
        #                ],
        # "G2_msg2-inrpc": [
        #                    {"hostname": "10.99.70.65"},
        #                ],
        # "G1_timer-inrpc": [
        #                    {"hostname": "10.99.70.66"},
        #                ],
        # "G2_timer-inrpc": [
        #                    {"hostname": "10.99.70.67"},
        #                ],
    }
}

version_data = {
    "jpol":  {
        "G1_node-api": {
            "version": "v1.0.0",
            "build": 2,
        },
        "G2_node-api": {
            "version": "v1.0.0",
            "build": 4,
        },
        "G1_mb-inrpc": {
            "version": "v1.6.16",
            "build": 47,
        },
        "G2_mb-inrpc": {
            "version": "v1.6.16",
            "build": 48,
        },
        "G1_planner-inrpc": {
            "version": "v3.0.14",
            "build": 2,
        },
        "G2_planner-inrpc": {
            "version": "v3.0.14",
            "build": 2,
        },
        "G1_msg2-inrpc": {
            "version": "v1.6.16",
            "build": 45,
        },
        "G2_msg2-inrpc": {
            "version": "v1.6.16",
            "build": 45,
        },
        "G1_timer-inrpc": {
            "version": "v1.1.14",
            "build": 1,
        },
        "G2_timer-inrpc": {
            "version": "v1.1.14",
            "build": 1,
        },
    }
}

inventory_data =  {
    "jpol": {
                "G1_node-api": {
                    "hosts": hosts_data["jpol"]["G1_node-api"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "node-api",
                             "version": version_data["jpol"]["G1_node-api"]["version"],
                             "build": version_data["jpol"]["G1_node-api"]["build"],
                             }
                },
                "G2_node-api": {
                    "hosts": hosts_data["jpol"]["G2_node-api"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "node-api",
                             "version": version_data["jpol"]["G2_node-api"]["version"],
                             "build": version_data["jpol"]["G2_node-api"]["build"],
                             }
                },
                "G1_mb-inrpc": {
                    "hosts": hosts_data["jpol"]["G1_mb-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "mb-inrpc",
                             "version": version_data["jpol"]["G1_mb-inrpc"]["version"],
                             "build": version_data["jpol"]["G1_mb-inrpc"]["build"],
                             }
                },
                "G2_mb-inrpc": {
                    "hosts": hosts_data["jpol"]["G2_mb-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "mb-inrpc",
                             "version": version_data["jpol"]["G2_mb-inrpc"]["version"],
                             "build": version_data["jpol"]["G2_mb-inrpc"]["build"],
                             }
                },
                "G1_planner-inrpc": {
                    "hosts": hosts_data["jpol"]["G1_planner-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "planner-inrpc",
                             "version": version_data["jpol"]["G1_planner-inrpc"]["version"],
                             "build": version_data["jpol"]["G1_planner-inrpc"]["build"],
                             }
                },
                "G2_planner-inrpc": {
                    "hosts": hosts_data["jpol"]["G2_planner-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "planner-inrpc",
                             "version": version_data["jpol"]["G2_planner-inrpc"]["version"],
                             "build": version_data["jpol"]["G2_planner-inrpc"]["build"],
                             }
                },
                "G1_msg2-inrpc": {
                    "hosts": hosts_data["jpol"]["G1_msg2-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "msg2-inrpc",
                             "version": version_data["jpol"]["G1_msg2-inrpc"]["version"],
                             "build": version_data["jpol"]["G1_msg2-inrpc"]["build"],
                             }
                },
                "G2_msg2-inrpc": {
                    "hosts": hosts_data["jpol"]["G2_msg2-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "msg2-inrpc",
                             "version": version_data["jpol"]["G2_msg2-inrpc"]["version"],
                             "build": version_data["jpol"]["G2_msg2-inrpc"]["build"],
                             }
                },
                "G1_timer-inrpc": {
                    "hosts": hosts_data["jpol"]["G1_timer-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "timer-inrpc",
                             "version": version_data["jpol"]["G1_timer-inrpc"]["version"],
                             "build": version_data["jpol"]["G1_timer-inrpc"]["build"],
                             }
                },
                "G2_timer-inrpc": {
                    "hosts": hosts_data["jpol"]["G2_timer-inrpc"],
                    "vars": {
                             "env":"test",
                             "project":"jpol",
                             "module": "timer-inrpc",
                             "version": version_data["jpol"]["G2_timer-inrpc"]["version"],
                             "build": version_data["jpol"]["G2_timer-inrpc"]["build"],
                             }
                },
            }
}