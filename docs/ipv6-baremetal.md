# IPv6 Support for Baremetal Deployments

CephCI supports IPv6 single-stack networking for baremetal deployments. IPv4 remains the default. When IPv6 is enabled, SSH access to target nodes is routed through a jump host (bastion) that bridges the IPv4 CI network and the IPv6 cluster network.

## Network Topology

```
CI runner --IPv4--> jump host (bastion) --IPv6--> target nodes
```

- The CI runner connects to the jump host over IPv4.
- The jump host forwards SSH connections to IPv6 target nodes via a `direct-tcpip` channel.
- All Ceph cluster traffic runs over IPv6.

## Configuration

IPv6 is configured entirely through the cluster YAML under `globals`. Two new keys are used: `ip_version` (under `networks`) and `jump_host` (top-level under `ceph-cluster`).

### Minimal Example

```yaml
globals:
  - ceph-cluster:
      name: ceph
      jump_host:
        hostname: bastion.example.com
        ip: 10.1.1.100
        username: root
        password: mypass
      networks:
        public:
          - fd00::/64
        ip_version: ipv6
      nodes:
        - hostname: osd-0.example.com
          id: node1
          ip: fd00::a01:70a6
          role: [_admin, installer, osd]
          root_private_key: ~/.ssh/id_rsa
          volumes: [/dev/sda]
```

### Configuration Reference

#### `networks.ip_version`

| Value    | Behavior |
|----------|----------|
| `ipv4`   | Default. Standard IPv4 networking, no jump host required. |
| `ipv6`   | IPv6 single-stack. Requires `jump_host` to be set. |

When omitted, defaults to `ipv4` and all existing behavior is unchanged.

#### `jump_host`

| Field         | Required | Description |
|---------------|----------|-------------|
| `hostname`    | No       | Hostname of the bastion (informational). |
| `ip`          | Yes      | IPv4 address reachable from the CI runner. |
| `username`    | Yes      | SSH username on the bastion. |
| `password`    | No*      | SSH password for the bastion. |
| `private_key` | No*      | Path to SSH private key for the bastion. |

\* Provide either `password` or `private_key` for authentication.

#### `nodes[].ip`

For IPv6 clusters, each node's `ip` must be an IPv6 address reachable from the jump host.

## DNS / Host Resolution Prerequisite

On IPv6 clusters, each target node's short hostname must resolve to its IPv6 address. This is needed because `search_ethernet_interface()` pings nodes by shortname to discover the correct network interface.

Ensure one of the following before deployment:

- **AAAA DNS records** exist for each node's hostname, or
- **`/etc/hosts`** on each target node maps peer shortnames to IPv6 addresses.

## What Changes With IPv6

When `ip_version: ipv6` is set:

- **SSH connections** are proxied through the jump host. The CI runner connects to the bastion over IPv4, then a forwarding channel reaches each IPv6 node.
- **`set_internal_ip()`** discovers the node's global-scope IPv6 address (filtering out link-local `fe80::` addresses) instead of parsing `ifconfig eth0`.
- **`search_ethernet_interface()`** uses `ping -6` instead of `ping` when probing interfaces.
- **`create_ceph_conf()`** wraps monitor IPs in brackets (`[fd00::1]`) as required by Ceph's `mon host` configuration.
- **`find_free_port()`** binds to `::1` with `AF_INET6` instead of `localhost` with `AF_INET`.

## What Does Not Change

- **`cephadm bootstrap --mon-ip`**: cephadm accepts bare IPv6 addresses natively.
- **TCP keepalive sysctls**: `/proc/sys/net/ipv4/tcp_keepalive_*` applies to all TCP sockets (including IPv6) on Linux.
- **Paramiko SSH**: supports IPv6 addresses natively when given the forwarding channel from the jump host.
- **`ssl_certs.py`**: already uses `ipaddress.ip_address()` which handles IPv6.

## IPv4 Backward Compatibility

All new code paths are guarded by `if ipv6` / `if jump_host` checks. When `ip_version` is absent and `jump_host` is absent (the case for all existing IPv4 configs), every branch falls through to the original unmodified code. No changes to existing IPv4 deployments are required.

## Utility Module

`utility/ipv6_utils.py` provides helper functions used throughout the codebase:

| Function | Purpose |
|----------|---------|
| `is_ipv6_address(addr)` | Returns `True` if `addr` is a valid IPv6 address. |
| `format_ip_for_url(addr)` | Wraps IPv6 in brackets (`[fd00::1]`), passes IPv4 through. |
| `format_ip_for_ceph_mon(addr)` | Same bracket wrapping for `mon host` config entries. |
| `resolve_hostname(hostname, prefer_ipv6=False)` | Resolves using `getaddrinfo` with fallback across address families. |

All functions are no-ops for IPv4 inputs.

## Scope and Limitations

This implementation covers the infrastructure layer only (SSH connectivity, IP discovery, config generation). The following are not yet supported and can be added when IPv6 test suites are needed:

- CephFS kernel mount address formatting
- NFS mount address formatting
- Dashboard URL formatting
- REST API client URL formatting
