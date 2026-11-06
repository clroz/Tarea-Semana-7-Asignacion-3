# Informe técnico

## Alcance

El laboratorio verifica el direccionamiento de la LAN, la asignación automática de una dirección al servidor Zabbix y la supervisión del router y del switch mediante SNMP de solo lectura. Toda la configuración se realiza sobre los tres nodos del archivo PNETLab: Docker/Ubuntu, Cisco IOSv L2 y Zabbix Appliance.

## Diseño de red

La LAN utiliza `192.168.7.0/24`. El router Ubuntu conecta al switch por `eth1` en la red PNETLab `network 2`; el servidor Zabbix conecta al switch por `e0` en `network 1`. El switch une ambas redes en VLAN 1.

| Función | Valor |
|---|---|
| Router LAN | `192.168.7.1/24` |
| SVI del switch | `192.168.7.2/24` |
| Gateway anunciado por DHCP | `192.168.7.1` |
| Pool DHCP | `192.168.7.100–192.168.7.199` |
| Reserva DHCP del appliance Zabbix | `192.168.7.194` |
| SNMP | v2c, comunidad `LabZabbixRo-7`, solo lectura |

## Router Ubuntu (nodo Docker)

El archivo `scripts/router-start.sh` configura `eth1`, habilita reenvío IP, instala `dnsmasq`, `snmpd` e `iptables` si faltan, y levanta los servicios. El hook PNETLab `scripts/config_docker_router.py` arranca ese script cada vez que inicia el nodo Docker.

`dnsmasq` entrega máscara `/24`, gateway `192.168.7.1`, DNS local y una reserva `192.168.7.194` para la MAC del appliance Zabbix. `snmpd` escucha en `192.168.7.1:161` y permite consultas de solo lectura desde `192.168.7.0/24`.

## Switch Cisco

La interfaz `Vlan1` tiene `192.168.7.2/24`, gateway `192.168.7.1`. Los puertos `Gi0/0` y `Gi0/1` son puertos de acceso en VLAN 1. La comunidad SNMP está configurada como `RO` y limitada con la lista de acceso 10 a `192.168.7.0/24`.

## Zabbix

El appliance Zabbix 7.0.32 usa DHCP y recibe la dirección reservada `192.168.7.194`. Se registraron dos hosts con interfaces SNMPv2c:

- `Router Ubuntu Docker`, `192.168.7.1`, plantilla `Linux by SNMP`.
- `Switch SW1`, `192.168.7.2`, plantilla `Cisco IOS by SNMP`.

La macro `{$SNMP_COMMUNITY}` contiene la comunidad de laboratorio. Zabbix indicó disponibilidad SNMP para ambas interfaces y guardó el dato `System description` de cada dispositivo. La evidencia resumida está en [`evidencia-snmp.json`](evidencia-snmp.json).

## Verificación ejecutada

1. Ubuntu recibe DHCP y llega a `192.168.7.1` y `192.168.7.2`.
2. El switch responde a pings al router y al servidor Zabbix.
3. Zabbix recibió por DHCP la reserva `192.168.7.194`.
4. La interfaz web y la API de Zabbix respondieron en `192.168.7.194`.
5. La API mostró ambas interfaces SNMP como disponibles y valores `sysDescr.0` reales.
6. Se reinició el nodo Docker y se confirmó que su hook volvió a levantar DHCP y SNMP.

## Archivos de configuración

Los archivos exportados del switch y los servicios del router están en `running-configs/`. El archivo de laboratorio listo para importar está en `lab/Tarea-Semana-7.unl`. Las imágenes de appliance se descargan e instalan localmente en PNETLab; no se suben al repositorio por su tamaño.
