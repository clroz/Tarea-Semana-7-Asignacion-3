#!/usr/bin/env bash
set -euo pipefail

if ! command -v dnsmasq >/dev/null || ! command -v snmpd >/dev/null || ! command -v iptables >/dev/null; then
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y dnsmasq snmpd iptables
fi

ip link set eth1 up
ip addr replace 192.168.7.1/24 dev eth1
sysctl -w net.ipv4.ip_forward=1 >/dev/null
printf 'nameserver 8.8.8.8\n' > /etc/resolv.conf

cat > /etc/dnsmasq-router.conf <<'EOF'
port=53
interface=eth1
bind-interfaces
no-resolv
dhcp-authoritative
dhcp-range=192.168.7.100,192.168.7.199,255.255.255.0,12h
dhcp-host=50:4d:a0:00:03:00,192.168.7.194,zabbix-server
dhcp-option=option:router,192.168.7.1
dhcp-option=option:dns-server,192.168.7.1
domain=lab.local
local=/lab.local/
address=/router.lab.local/192.168.7.1
address=/zabbix.lab.local/192.168.7.194
log-dhcp
log-facility=/var/log/dnsmasq-router.log
EOF

cat > /etc/snmp/snmpd.conf <<'EOF'
agentaddress udp:192.168.7.1:161
rocommunity LabZabbixRo-7 192.168.7.0/24
sysName Router-Ubuntu-Docker
sysDescr Ubuntu 20.04 router/DHCP node
sysLocation Laboratorio-Seguridad-Redes
sysContact administrador
sysServices 72
EOF

pkill -x dnsmasq 2>/dev/null || true
pkill -x snmpd 2>/dev/null || true
sleep 1
dnsmasq --conf-file=/etc/dnsmasq-router.conf
snmpd -C -c /etc/snmp/snmpd.conf -Lf /var/log/snmpd-router.log -p /run/snmpd-router.pid
