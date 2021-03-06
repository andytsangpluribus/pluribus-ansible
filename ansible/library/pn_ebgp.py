#!/usr/bin/python
""" PN CLI Zero Touch Provisioning (ZTP) with EBGP"""

#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#

import shlex

DOCUMENTATION = """
---
module: pn_ztp_ebgp
author: "Pluribus Networks (@gauravbajaj)"
version: 1
short_description: CLI command to do zero touch provisioning with ebgp.
description:
    Zero Touch Provisioning (ZTP) allows you to provision new switches in your
    network automatically, without manual intervention.
    It performs following steps:
        - Assigning bgp_as
        - Configuring bgp_redistribute
        - Configuring bgp_maxpath
        - Assign bgp_neighbor
        - Assign router_id
        - Create leaf_cluster
options:
    pn_cliusername:
        description:
          - Provide login username if user is not root.
        required: False
        type: str
    pn_clipassword:
      description:
        - Provide login password if user is not root.
      required: False
      type: str
    pn_cliswitch:
      description:
        - Target switch(es) to run the CLI on.
      required: False
      type: str
    pn_spine_list:
      description:
        - Specify list of Spine hosts
      required: False
      type: list
    pn_leaf_list:
      description:
        - Specify list of leaf hosts
      required: False
      type: list
"""

EXAMPLES = """
    - name: Configure eBGP
      pn_ebgp:
        pn_cliusername: "{{ USERNAME }}"
        pn_clipassword: "{{ PASSWORD }}"
        pn_spine_list: "{{ groups['spine'] }}"
        pn_leaf_list: "{{ groups['leaf'] }}"
"""

RETURN = """
msg:
  description: The set of responses for each command.
  returned: always
  type: str
changed:
  description: Indicates whether the CLI caused changes on the target.
  returned: always
  type: bool
"""


def pn_cli(module):
    """
    This method is to generate the cli portion to launch the Netvisor cli.
    It parses the username, password, switch parameters from module.
    :param module: The Ansible module to fetch username, password and switch
    :return: The cli string for further processing
    """
    username = module.params['pn_cliusername']
    password = module.params['pn_clipassword']
    cliswitch = module.params['pn_cliswitch']
    if username and password:
        cli = '/usr/bin/cli --quiet --user %s:%s' % (username, password)
    else:
        cli = '/usr/bin/cli --quiet '

    if cliswitch:
        cli += ' switch ' + cliswitch

    return cli


def run_cli(module, cli):
    """
    This method executes the cli command on the target node(s) and returns the
    output.
    :param module: The Ansible module to fetch input parameters.
    :param cli: the complete cli string to be executed on the target node(s).
    :return: Output/Error or Success message depending upon
    the response from cli.
    """
    cli = shlex.split(cli)
    rc, out, err = module.run_command(cli)
    if out:
        return out

    if err:
        module.exit_json(
            error="1",
            failed=True,
            stderr=err.strip(),
            msg="Operation Failed: " + str(cli),
            changed=False
        )
    else:
        return 'Success'


def assigning_bgp_as(module, bgp_as):
    """
    This method assigns bgp_as to vrouter.
    :param module: The Ansible module to fetch input parameters.
    :param bgp_as: The user_input for the bgp_as to be assigned.
    :return: The output message of the assignment of the bgp_as
    """
    output = ' '
    bgp_as_spine = bgp_as
    bgp_leaf = int(bgp_as) + 1
    spine_list = module.params['pn_spine_list']

    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    cli += ' vrouter-show format name no-show-headers '
    vrouter_names = run_cli(module, cli).split()

    if len(vrouter_names) > 0:
        for vrouter in vrouter_names:
            cli = clicopy
            cli += ' vrouter-show name ' + vrouter
            cli += ' format location no-show-headers '
            switch_vrouter = run_cli(module, cli).split()
            if switch_vrouter[0] in spine_list:
                cli = clicopy
                cli += ' vrouter-modify name %s bgp-as %s ' % (vrouter,
                                                               bgp_as_spine)
                output += run_cli(module, cli)
                output += ' '
            else:
                cli = clicopy
                cli += ' vrouter-modify name %s bgp-as %s ' % (vrouter,
                                                               str(bgp_leaf))
                output += run_cli(module, cli)
                output += ' '
                bgp_leaf += 1
    else:
        output += 'No vrouters present/created in this switch'

    return output


def bgp_neighbor(module):
    """
    This method add bgp_neighbor to the vrouter.
    :param module: The Ansible module to fetch input parameters.
    :return: The output of the adding bgp-neighbor
    """
    output = ' '
    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    cli += ' vrouter-show format name no-show-headers '
    vrouter_names = run_cli(module, cli).split()

    if len(vrouter_names) > 0:
        for vrouter in vrouter_names:
            cli = clicopy
            cli += ' vrouter-show name %s ' % vrouter
            cli += ' format location no-show-headers '
            switch = run_cli(module, cli).split()

            cli = clicopy
            cli += ' vrouter-interface-show vrouter-name %s ' % vrouter
            cli += ' format l3-port no-show-headers '
            port_num = run_cli(module, cli).split()
            port_num = list(set(port_num))
            port_num.remove(vrouter)

            for port in port_num:
                cli = clicopy
                cli += ' switch %s port-show port %s ' % (switch[0], port)
                cli += ' format hostname no-show-headers '
                hostname = run_cli(module, cli).split()

                cli = clicopy
                cli += ' vrouter-show location %s ' % hostname[0]
                cli += ' format bgp-as no-show-headers '
                bgp_hostname = run_cli(module, cli).split()

                cli = clicopy
                cli += ' switch %s port-show port %s ' % (switch[0], port)
                cli += ' format rport no-show-headers '
                port_hostname = run_cli(module, cli)

                cli = clicopy
                cli += ' vrouter-show location %s ' % hostname[0]
                cli += ' format name no-show-headers '
                vrouter_hostname = run_cli(module, cli).split()

                cli = clicopy
                cli += ' vrouter-interface-show vrouter-name %s ' % (
                    vrouter_hostname[0])
                cli += ' l3-port %s format ip no-show-headers ' % port_hostname
                ip_hostname_subnet = run_cli(module, cli).split()
                ip_hostname_subnet.remove(vrouter_hostname[0])

                ip_hostname_subnet = ip_hostname_subnet[0].split('/')
                ip_hostname = ip_hostname_subnet[0]

                cli = clicopy
                cli += ' vrouter-bgp-show remote-as ' + bgp_hostname[0]
                cli += ' neighbor %s format switch no-show-headers ' % (
                    ip_hostname)
                already_added = run_cli(module, cli).split()

                if vrouter in already_added:
                    output += " already exists bgp in %s " % vrouter
                    output += ' '
                else:
                    cli = clicopy
                    cli += ' vrouter-bgp-add vrouter-name ' + vrouter
                    cli += ' neighbor %s remote-as %s ' % (
                        ip_hostname, bgp_hostname[0])
                    output += run_cli(module, cli)
                    output += ' added bgp %s ' % vrouter
    else:
        print "no vrouter created yet"

    return output


def assign_router_id(module):
    """
    This method assign router id same as loopback ip.
    :param module: The Ansible module to fetch input parameters.
    :return: The output message for the assignment.
    """
    output = ' '
    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    cli += ' vrouter-show format name no-show-headers '
    vrouter_names = run_cli(module, cli).split()

    if len(vrouter_names) > 0:
        for vrouter in vrouter_names:
            cli = clicopy
            cli += ' vrouter-loopback-interface-show vrouter-name ' + vrouter
            cli += ' format ip no-show-headers '
            loopback_ip = run_cli(module, cli).split()
            loopback_ip.remove(vrouter)

            cli = clicopy
            cli += ' vrouter-modify name %s router-id %s ' % (vrouter,
                                                              loopback_ip[0])
            output += run_cli(module, cli)
            output += ' '
    else:
        print 'No vrouters present/created in this switch.'

    return output


def bgp_redistribute(module, bgp_redis):
    """
    This method assigns bgp_redistribute to the vrouter.
    :param module: The Ansible module to fetch input parameters.
    :param bgp_redis: It is 'connected' by default.
    :return: The output message for the assignment.
    """
    output = ' '
    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    cli += ' vrouter-show format name no-show-headers '
    vrouter_names = run_cli(module, cli).split()

    for vrouter in vrouter_names:
        cli = clicopy
        cli += ' vrouter-modify name %s bgp-redistribute %s ' % (vrouter,
                                                                 bgp_redis)
        output += run_cli(module, cli)
        output += ' '

    return output


def bgp_maxpath(module, bgp_max):
    """
    This method assigns bgp_maxpath to the vrouter.
    :param module: The Ansible module to fetch input parameters.
    :param bgp_max: It is '16' by default.
    :return: The output message for the assignment.
    """
    output = ' '
    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    cli += ' vrouter-show format name no-show-headers '
    vrouter_names = run_cli(module, cli).split()

    for vrouter in vrouter_names:
        cli = clicopy
        cli += ' vrouter-modify name %s bgp-max-paths %s ' % (vrouter,
                                                              bgp_max)
        output += run_cli(module, cli)
        output += ' '

    return output


def leaf_no_cluster(module, leaf_list):
    """
    This method is to find leafs not in any leafs
    :param module: The Ansible module to fetch input parameters.
    :param leaf_list: The list of all the leaf switches.
    :return: The list of leaf in no cluster.
    """
    cli = pn_cli(module)
    noncluster_leaf = []
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    clicopy += ' cluster-show format cluster-node-1 no-show-headers '
    cluster1 = run_cli(module, clicopy).split()
    clicopy = cli
    clicopy += ' cluster-show format cluster-node-2 no-show-headers '
    cluster2 = run_cli(module, clicopy).split()

    for leaf in leaf_list:
        if (leaf not in cluster1) and (leaf not in cluster2):
            noncluster_leaf.append(leaf)

    return noncluster_leaf


def create_cluster(module, switch, name, node1, node2):
    """
    This method is to create a cluster between two switches.
    :param module: The Ansible module to fetch input parameters.
    :param switch: Name of the local switch.
    :param name: The name of the cluster to create.
    :param node1: First node of the cluster.
    :param node2: Second node of the cluster.
    :return: The output of run_cli() method.
    """
    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    cli += ' switch %s cluster-show format name no-show-headers ' % node1
    cluster_list = run_cli(module, cli).split()
    if name not in cluster_list:
        cli = clicopy
        cli += ' switch %s cluster-create name %s ' % (switch, name)
        cli += ' cluster-node-1 %s cluster-node-2 %s ' % (node1, node2)
        return run_cli(module, cli)
    else:
        return "Already part of a cluster"


def leaf_cluster_formation(module, noncluster_leaf, spine_list):
    """
    This method uses non-clistered leafs and forms cluster
    :param module: The Ansible module to fetch input parameters.
    :param noncluster_leaf: List of all the leaf not in cluster.
    :param spine_list: The list of spines.
    :return: The output message of success or error
    """
    cli = pn_cli(module)
    if 'switch' in cli:
        cli = cli.rpartition('switch')[0]

    clicopy = cli
    output = ' '
    flag = 0
    while flag == 0:
        if len(noncluster_leaf) == 0:
            output += "no more leaf to create cluster"
            output += ' '
            flag += 1
        else:
            node1 = noncluster_leaf[0]
            noncluster_leaf.remove(node1)
            cli = clicopy
            cli += ' switch %s lldp-show ' % node1
            cli += ' format sys-name no-show-headers '
            system_names = run_cli(module, cli).split()
            system_names = list(set(system_names))

            cluster_flag = 0
            cluster_count = 0
            while (cluster_count < len(system_names)) and (cluster_flag == 0):
                switch = system_names[cluster_count]
                if switch not in spine_list:
                    if switch in noncluster_leaf:
                        name = node1 + '-to-' + switch + '-cluster'
                        output += create_cluster(module, switch, name, node1,
                                                 switch)
                        output += ' '
                        noncluster_leaf.remove(switch)
                        cluster_flag += 1
                    else:
                        print "switch already has a cluster"
                else:
                    print "switch is a spine"

                cluster_count += 1

    return output


def create_leaf_cluster(module):
    """
    This method creates leaf cluster with physical link
    :param module: The Ansible module to fetch input parameters.
    :return: The output message with success or error.
    """
    output = ' '
    spine_list = module.params['pn_spine_list']
    leaf_list = module.params['pn_leaf_list']
    noncluster_leaf = leaf_no_cluster(module, leaf_list)
    output += leaf_cluster_formation(module, noncluster_leaf, spine_list)
    output += ' '
    return output


def main():
    """ This section is for arguments parsing """

    module = AnsibleModule(
        argument_spec=dict(
            pn_cliusername=dict(required=False, type='str'),
            pn_clipassword=dict(required=False, type='str', no_log=True),
            pn_cliswitch=dict(required=False, type='str'),
            pn_fabric_retry=dict(required=False, type='int', default=1),
            pn_spine_list=dict(required=False, type='list'),
            pn_leaf_list=dict(required=False, type='list'),
            pn_bgp_as_range=dict(required=False, type='str', default='65000'),
            pn_bgp_redistribute=dict(required=False, type='str',
                                     choices=['none', 'static', 'connected',
                                              'rip', 'ospf'],
                                     default='connected'),
            pn_bgp_maxpath=dict(required=False, type='str', default='16')
        )
    )

    bgp_as_range = module.params['pn_bgp_as_range']
    bgp_redistribute_val = module.params['pn_bgp_redistribute']
    bgp_maxpath_val = module.params['pn_bgp_maxpath']

    message = ' '
    assigning_bgp_as(module, bgp_as_range)
    message += ' Assigned BGP_AS to vrouters '
    bgp_redistribute(module, bgp_redistribute_val)
    message += ' Assigned BGP_REDISTRIBUTE to vrouters '
    bgp_maxpath(module, bgp_maxpath_val)
    message += ' Assigned BGP_MAXPATH to vrouters '
    bgp_neighbor(module)
    message += ' Added BGP neighbors for vrouters '
    assign_router_id(module)
    message += ' Assigned ID to vrouters '
    create_leaf_cluster(module)
    message += ' Created leaf cluster with physical links '

    module.exit_json(
        stdout=message,
        error="0",
        failed=False,
        msg="eBGP setup completed successfully.",
        changed=True
    )

# AnsibleModule boilerplate
from ansible.module_utils.basic import AnsibleModule

if __name__ == '__main__':
    main()

