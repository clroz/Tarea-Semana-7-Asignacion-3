#!/usr/bin/env python3
"""Register the lab router and switch in the Zabbix appliance through its API."""

import argparse
import json
import urllib.request


def api(url, method, params, auth=None):
    request_data = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    if auth:
        request_data["auth"] = auth
    request = urllib.request.Request(
        url,
        data=json.dumps(request_data).encode("utf-8"),
        headers={"Content-Type": "application/json-rpc"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
    if "error" in result:
        raise RuntimeError(result["error"].get("data", result["error"]))
    return result["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://zabbix.lab.local/api_jsonrpc.php")
    parser.add_argument("--username", default="Admin")
    parser.add_argument("--password", required=True)
    parser.add_argument("--community", default="LabZabbixRo-7")
    args = parser.parse_args()

    token = api(args.url, "user.login", {"username": args.username, "password": args.password})
    groups = api(args.url, "hostgroup.get", {"output": ["groupid", "name"], "filter": {"name": ["Network devices"]}}, token)
    if groups:
        group_id = groups[0]["groupid"]
    else:
        group_id = api(args.url, "hostgroup.create", {"name": "Network devices"}, token)["groupids"][0]

    templates = {}
    for name in ("Linux by SNMP", "Cisco IOS by SNMP"):
        found = api(args.url, "template.get", {"output": ["templateid", "host"], "filter": {"name": [name]}}, token)
        if not found:
            raise RuntimeError("Zabbix template not found: " + name)
        templates[name] = found[0]["templateid"]

    devices = [
        ("R1-Ubuntu-Docker", "Router Ubuntu Docker", "192.168.7.1", "Linux by SNMP"),
        ("SW1-Cisco-IOSv", "Switch SW1", "192.168.7.2", "Cisco IOS by SNMP"),
    ]
    for host, label, address, template in devices:
        interface = {
            "type": 2,
            "main": 1,
            "useip": 1,
            "ip": address,
            "dns": "",
            "port": "161",
            "details": {"version": 2, "community": "{$SNMP_COMMUNITY}", "max_repetitions": 10},
        }
        existing = api(args.url, "host.get", {
            "output": ["hostid", "host"],
            "selectInterfaces": "extend",
            "filter": {"host": [host]},
        }, token)
        if existing:
            current = existing[0]
            old_snmp = next((item for item in current.get("interfaces", []) if item["type"] == "2"), None)
            if old_snmp:
                interface["interfaceid"] = old_snmp["interfaceid"]
            result = api(args.url, "host.update", {
                "hostid": current["hostid"],
                "name": label,
                "groups": [{"groupid": group_id}],
                "templates": [{"templateid": templates[template]}],
                "interfaces": [interface],
                "macros": [{"macro": "{$SNMP_COMMUNITY}", "value": args.community}],
            }, token)
            print("updated", host, result["hostids"][0])
        else:
            result = api(args.url, "host.create", {
                "host": host,
                "name": label,
                "groups": [{"groupid": group_id}],
                "templates": [{"templateid": templates[template]}],
                "interfaces": [interface],
                "macros": [{"macro": "{$SNMP_COMMUNITY}", "value": args.community}],
            }, token)
            print("created", host, result["hostids"][0])


if __name__ == "__main__":
    main()
