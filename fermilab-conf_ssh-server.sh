#!/bin/bash -u
FNALIPS="131.225.0.0/16,2620:006A:0000::/44,2001:0400:2410::/48"
REPLACE='131.225'
LINKLOCALIPS="169.254.0.0/16,FE80::/10,FC00::/7,FD00::/7"
DEBUG='FALSE'
SSHD_CONFIG='/etc/ssh/sshd_config'

# setup args in the right order for making getopt evaluation
# nice and easy.  You'll need to read the manpages for more info
args=$(getopt -o hdn:f:r: -- "$@")
eval set -- "$args"

###########################################################
usage() {
    echo ''           >&2
    echo "$0 [-d] [-l] [-n <network>] [-f /etc/ssh/sshd_config] [-r 131.225.*]" >&2
    echo "   Change /etc/ssh/sshd_config to meet Fermilab's standards"     >&2
    echo ''                                                                >&2
    echo '     -d enable debugging outupt'                                 >&2
    echo '     -n specify the network to consider FNAL'                    >&2
    echo '          NOTE: this replaces the default list'                  >&2
    echo '     -f use this sshd_config file'                               >&2
    echo '     -l leave link-local range alone'                            >&2
    echo '     -r replace the match entry containing this value'           >&2
    echo '          NOTE: if the entry is not found one will be created'   >&2
    echo " I believe the FNAL networks are:"                               >&2
    for net in $(echo ${FNALIPS} | tr ',' '\012'); do
        echo "    - ${net}"                                             >&2
    done
    echo ''                                                             >&2
    echo "  Examples:"                                                  >&2
    echo "    $0 -n 131.225.*"                                          >&2
    echo "    $0 -n 131.225.* -f /my/config"                            >&2
    echo "    $0 -n 131.225.* -f /my/config -r 131.225.*"               >&2


    exit 1
}

###########################################################
READ_HOSTFILE='FALSE'
HOSTFILE=$(mktemp)
for arg in $@; do
    case $1 in
        -- )
            # end of getopt args, shift off the -- and get out of the loop
            shift
            break 2
           ;;
         -d )
            # enable debugging
            DEBUG='TRUE'
            shift
           ;;
         -l )
            # don't do link local work
            LINKLOCALIPS=""
            shift
           ;;
         -f )
            # which config file?
            SSHD_CONFIG=$(readlink -f $2)
            shift
            shift
           ;;
         -r )
            # replace what entry
            REPLACE=$2
            shift
            shift
           ;;
         -s )
            # what host (list)?
            READ_HOSTFILE='TRUE'
            echo $2 >> ${HOSTFILE}
            shift
            shift
           ;;
         -h )
            # get help
            usage
           ;;

    esac
done

IFS="
"

if [[ "${DEBUG}" == 'TRUE' ]]; then
    set -x
fi

which augtool >/dev/null 2>&1
if [[ $? -ne 0 ]]; then
    echo "Could not find augtool" >&2
    exit 1
fi

if [[ "${READ_HOSTFILE}" == 'TRUE' ]]; then
    # Read revised IP list from file
    FNALIPS=$(cat ${HOSTFILE} | tr '\012' ',')
fi
rm -f ${HOSTFILE}

if [[ "x${LINKLOCALIPS}" != 'x' ]]; then
    # Add link local addresses to the restricted permissions
    FNALIPS="${FNALIPS},${LINKLOCALIPS}"
fi

########################################################################
if [[ -f ${SSHD_CONFIG} ]]; then
    cp -p ${SSHD_CONFIG} ${SSHD_CONFIG}.rpmsave
else
    echo "No such file ${SSHD_CONFIG}" >&2
    exit 1
fi

TMPFILE=$(mktemp)

########################################################################
# Setup universal defaults

cat > ${TMPFILE} <<EOF
set /files${SSHD_CONFIG}/GSSAPICleanupCredentials yes
set /files${SSHD_CONFIG}/GSSAPIKeyExchange yes
set /files${SSHD_CONFIG}/GSSAPIStrictAcceptorCheck yes
set /files${SSHD_CONFIG}/X11Forwarding yes
set /files${SSHD_CONFIG}/StrictModes yes
set /files${SSHD_CONFIG}/UsePAM yes

set /files${SSHD_CONFIG}/ChallengeResponseAuthentication no

set /files${SSHD_CONFIG}/Protocol 2

set /files${SSHD_CONFIG}/UsePrivilegeSeparation sandbox

save

EOF

if [[ "${DEBUG}" == 'TRUE' ]]; then
    echo "Setting global defaults"
    cat ${TMPFILE}
fi

augtool -t "Sshd incl ${SSHD_CONFIG}" >/dev/null <${TMPFILE}
if [[ $? -ne 0 ]]; then
    exit 1
fi

########################################################################
# See if the 'replace' entry exists, if not create it
cat > ${TMPFILE} <<EOF
match /files${SSHD_CONFIG}/Match/Condition/LocalAddress[ . =~ regexp(".*${REPLACE}.*") ]
EOF

if [[ "${DEBUG}" == 'TRUE' ]]; then
    echo "Finding an entry to replace"
    cat ${TMPFILE}
fi
MATCHES=$(augtool -t "Sshd incl ${SSHD_CONFIG}" <${TMPFILE})
if [[ $? -ne 0 ]]; then
    exit 1
fi
echo ${MATCHES} | grep -q '(no matches)'
if [[ $? -eq 0 ]]; then
    # host must have a sub value, so GSSAPIAuthentication yes is safe
    cat > ${TMPFILE} <<EOF
match /files${SSHD_CONFIG}/Match
EOF
    if [[ "${DEBUG}" == 'TRUE' ]]; then
        echo "No match found, determining if we are multivar already"
        cat ${TMPFILE}
    fi
    ALLMATCHES=$(augtool -t "Sshd incl ${SSHD_CONFIG}" <${TMPFILE})
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
    echo ${ALLMATCHES} | grep -q '(no matches)'
    if [[ $? -eq 0 ]]; then
        if [[ "${DEBUG}" == 'TRUE' ]]; then
            echo "No match stanzas in ${SSHD_CONFIG}"
        fi
        cat > ${TMPFILE} <<EOF
set /files${SSHD_CONFIG}/Match/Condition/LocalAddress ${FNALIPS}
set /files${SSHD_CONFIG}/Match/Settings/GSSAPIAuthentication yes

save
EOF
        if [[ "${DEBUG}" == 'TRUE' ]]; then
            echo "Making first match stanza"
            cat ${TMPFILE}
        fi
        augtool -t "Sshd incl ${SSHD_CONFIG}" >/dev/null <${TMPFILE}
        if [[ $? -ne 0 ]]; then
            exit 1
        fi
    else
        MATCHCOUNT=$(echo $ALLMATCHES | wc -l)
        if [[ "${DEBUG}" == 'TRUE' ]]; then
            echo "Found Matches"
            echo "${ALLMATCHES}"
            echo "I count them as : ${MATCHCOUNT}"
        fi
        if [[ ${MATCHCOUNT} -eq 1 ]]; then
            MATCHCOUNT='Match'
        else
            MATCHCOUNT='Match[1]'
        fi
        cat > ${TMPFILE} <<EOF
ins Match before /files${SSHD_CONFIG}/${MATCHCOUNT}
set /files${SSHD_CONFIG}/Match[1]/Condition/LocalAddress ${FNALIPS}
set /files${SSHD_CONFIG}/Match[1]/Settings/GSSAPIAuthentication yes

save
EOF
        if [[ "${DEBUG}" == 'TRUE' ]]; then
            echo "Setting up new match at top of file"
            cat ${TMPFILE}
        fi
        augtool -t "Sshd incl ${SSHD_CONFIG}" >/dev/null <${TMPFILE}
        if [[ $? -ne 0 ]]; then
            exit 1
        fi
    fi

else
    XPATH=$(echo ${MATCHES} | cut -d= -f1)
    cat > ${TMPFILE} <<EOF
set ${XPATH} '${FNALIPS}'

save
EOF
    if [[ "${DEBUG}" == 'TRUE' ]]; then
        echo "Replacing existing stanza-> ${MATCHES}"
        cat ${TMPFILE}
    fi
    augtool -t "Sshd incl ${SSHD_CONFIG}" >/dev/null <${TMPFILE}
    if [[ $? -ne 0 ]]; then
        exit 1
    fi
fi

########################################################################
# Find the FNAL network Match stanza
cat > ${TMPFILE} <<EOF
match /files${SSHD_CONFIG}/Match/Condition/LocalAddress
EOF
if [[ "${DEBUG}" == 'TRUE' ]]; then
    echo "Finding FNAL match stanza"
    cat ${TMPFILE}
fi
MYSTANZA=$(augtool -t "Sshd incl ${SSHD_CONFIG}" <${TMPFILE} |grep ${FNALIPS} | awk '{print $1}' | sed -e 's/Condition\/LocalAddress/Settings/')

if [[ "${DEBUG}" == 'TRUE' ]]; then
    echo "My match stanza is: ${MYSTANZA}"
fi

cat > ${TMPFILE} <<EOF
set ${MYSTANZA}/HostbasedAuthentication no
set ${MYSTANZA}/KbdInteractiveAuthentication no
set ${MYSTANZA}/PasswordAuthentication no
set ${MYSTANZA}/PubkeyAuthentication no
set ${MYSTANZA}/RhostsRSAAuthentication no
set ${MYSTANZA}/RSAAuthentication no

set ${MYSTANZA}/AllowAgentForwarding yes
set ${MYSTANZA}/AllowTcpForwarding yes
set ${MYSTANZA}/GSSAPIAuthentication yes
set ${MYSTANZA}/X11Forwarding yes

set ${MYSTANZA}/PermitRootLogin without-password

save

EOF

# Make changes to sshd_config
if [[ "${DEBUG}" == 'TRUE' ]]; then
    echo "Writing FNAL Match"
    cat ${TMPFILE}
fi
augtool -t "Sshd incl ${SSHD_CONFIG}" >/dev/null <${TMPFILE}
if [[ $? -ne 0 ]]; then
    exit 1
fi

########################################################################

rm -f ${TMPFILE}

########################################################################
# setup selinux context correctly on /root/.k5login, saves frustration later
# Ensure selinux context is correct for the config now that we are done with it
if [[ ! -e /root/.k5login ]]; then
    touch /root/.k5login >/dev/null 2>&1
fi
chown root:root /root/.k5login >/dev/null 2>&1
chmod 600 /root/.k5login >/dev/null 2>&1
restorecon -F /root/.k5login >/dev/null 2>&1
chmod 600 /etc/ssh/sshd_config >/dev/null 2>&1
restorecon -F /etc/ssh/sshd_config >/dev/null 2>&1

exit 0
