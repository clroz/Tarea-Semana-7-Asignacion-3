#!/usr/bin/env python3
"""PNETLab startup hook for the existing Ubuntu Docker router node."""

import getopt
import os
import re
import subprocess
import sys


def run(args, check=True):
    return subprocess.run(args, check=check, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)


def main():
    action = filename = docker_id = None
    try:
        opts, _ = getopt.getopt(sys.argv[1:], "a:i:t:f:", ["action=", "timeout=", "file="])
    except getopt.GetoptError as exc:
        print(exc, file=sys.stderr)
        return 2
    for opt, value in opts:
        if opt in ("-a", "--action"):
            action = value
        elif opt in ("-f", "--file"):
            filename = value
        elif opt == "-i":
            docker_id = value

    if action not in ("put", "get") or not filename or not docker_id:
        print("Usage: config_docker_router.py -a put|get -i ddockerN -f startup-config", file=sys.stderr)
        return 2

    match = re.search(r"(\d+)$", docker_id)
    if not match:
        print("Cannot determine Docker node number from " + docker_id, file=sys.stderr)
        return 2
    container = "docker" + match.group(1)
    inspect = ["/usr/bin/docker", "-H=tcp://127.0.0.1:4243", "inspect", "--format", "{{.State.Pid}}", container]
    try:
        pid = run(inspect).stdout.strip()
    except subprocess.CalledProcessError as exc:
        print(exc.stdout, file=sys.stderr)
        return 1
    if not pid or pid == "0":
        print("Docker node is not running: " + container, file=sys.stderr)
        return 1

    if action == "put":
        if not os.path.exists(filename):
            open(filename, "a", encoding="utf-8").close()
        with open(filename, encoding="utf-8") as config:
            for line in config:
                line = line.strip()
                if line and not line.startswith("#"):
                    run(["/opt/unetlab/wrappers/nsenter", "-t", pid, "-n", "/bin/sh", "-c", line])
        result = run(["/usr/bin/docker", "-H=tcp://127.0.0.1:4243", "exec", container,
                      "/bin/bash", "/usr/local/sbin/router-start.sh"], check=False)
        if result.returncode:
            print(result.stdout, file=sys.stderr)
            return result.returncode

        running_dir = os.path.dirname(filename)
        for marker in (".lock",):
            try:
                os.remove(os.path.join(running_dir, marker))
            except FileNotFoundError:
                pass
        open(os.path.join(running_dir, ".configured"), "a").close()
        return 0

    # Export only the ordinary PNETLab startup commands, using the real container name.
    result = run(["/opt/unetlab/scripts/config_docker.py", "-a", "get", "-i", container, "-f", filename], check=False)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
