Name:		fermilab-conf_ssh
Version:	1.0
Release:	6.1%{?dist}
Summary:	Configure SSH for use with Fermilab

Group:		Fermilab
License:	GPL
URL:		https://github.com/fermilab-context-rpms/fermilab-conf_ssh

BuildRequires:	coreutils
BuildArch:	noarch

Source0:	%{name}.tar.xz
%if 0%{?rhel} < 8 && 0%{?fedora} <= 27
Source1:	fermilab-conf_ssh-server.sh
%else
Requires:	(%{name}-client == %{version}-%{release} if openssh-clients)
Requires:	(%{name}-server == %{version}-%{release} if openssh-server)
%endif

%description
The default configuration for openssh is not fully suitable for use with
Fermilab.

Behavior from: CS-doc-1186


%package client
Summary:	Add Fermilab ssh_config to %{_sysconfdir}/ssh/ssh_config.d/
Requires:	openssh-clients > 7.8
Requires(post):	policycoreutils coreutils grep
%if 0%{?rhel} >= 8 || 0%{?fedora} >= 27
Recommends:	krb5-workstation
%endif

%description client
The default configuration for openssh-client does not take full advantage
of the expected Fermilab openssh-server settings.

This includes X11Forwarding and GSSAPI credential forwarding.

The default behavior of openssh-client includes files from %{_sysconfdir}/ssh/ssh_config.d/*.conf

Behavior from: CS-doc-1186

%package server
%if 0%{?rhel} >= 8 || 0%{?fedora} >= 27
Summary:	Add Fermilab sshd_config to %{_sysconfdir}/ssh/ssh_config.d/
%if 0%{?rhel} >= 9 || 0%{?fedora} >= 31
Conflicts:	openssh-server < 8.2
%else
Conflicts:	openssh-server < 8.0p1-12
%endif
%else
Summary:	Add Fermilab settings to %{_sysconfdir}/ssh/sshd_config
Conflicts:	openssh-server < 6.1
%endif
%if 0%{?rhel} >= 8 || 0%{?fedora} >= 27
Recommends:	krb5-workstation
Recommends:	openssh-server
Recommends:	xorg-x11-xauth
Recommends:	%{name}-client >= %{version}-%{release}
Suggests:	fermilab-conf_kerberos
Suggests:	fermilab-conf_timesync
%endif
Requires(post): policycoreutils coreutils grep systemd

%description server
The default configuration for openssh-server is not suitable for Fermilab.

This RPM will update the SSH Server config to meet Fermilab standards.

Requirement from: CS-doc-1186

%prep
%setup -q -n conf


%build


%install

# client
%{__install} -D client/fermilab_ssh-client.conf %{buildroot}/%{_sysconfdir}/ssh/ssh_config.d/fermilab_ssh-client.conf

# server
%if 0%{?rhel} >= 8 || 0%{?fedora} >= 27
%{__mkdir_p} %{buildroot}/etc/ssh/sshd_config.d/
%{__cp} server/* %{buildroot}/etc/ssh/sshd_config.d/

%post server -p /bin/bash
grep -q '^Include /etc/ssh/sshd_config.d/\*.conf' /etc/ssh/sshd_config
if [[ $? -ne 0 ]]; then
    echo 'Include /etc/ssh/sshd_config.d/*.conf' >> /etc/ssh/sshd_config
    %{_fixperms} /etc/ssh/sshd_config
    restorecon -F /etc/ssh/sshd_config
fi
systemctl -q is-active sshd.service
if [[ $? -eq 0 ]]; then
    systemctl condrestart sshd.service
fi
# make sure this has the right context, ownership, etc
touch /root/.k5login || :
%{__chown} root:root /root/.k5login || :
%{__chmod} 600 /root/.k5login || :
restorecon /root/.k5login || :
exit 0

%else
%{__install} -D %{SOURCE1} %{buildroot}/%{_libexecdir}/%{name}/%{name}.sh

%check
bash -n %{buildroot}/%{_libexecdir}/%{name}/%{name}.sh

#####################################################################
%triggerin -p /bin/bash -- openssh-server

##################### BEGIN Trigger Snippet #########################
set -u
TRIGGER_ON_PACKAGE_NAME='openssh-server'
# The following script snippet attempts to classify why we were called:
#  - on first install of either package, RUN_TRIGGER == "Initial"
#  - on upgrade of _THIS_ package, RUN_TRIGGER == "UpgradeSELF"
#  - on upgrade of the TRIGGERON package, RUN_TRIGGER == "UpgradeTRIGGERON"
#  - on upgrade of the TRIGGERON package but initial install of _THIS_ package, RUN_TRIGGER == "InitialSELFUpgradeTRIGGERON"
#  - on upgrade of the BOTH packages, RUN_TRIGGER == "UPGRADEALL"

CURRENT_INSTALLS_OF_THIS_PACKAGE=${1:-0}
TRIGGER_ON_PACKAGE=${2:-0}

RUN_TRIGGER="NO"
if [[ ${TRIGGER_ON_PACKAGE} -eq 1 ]]; then
    # We only get here if we are NOT doing an upgrade of the trigger package
    if [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -eq 0 ]]; then
        # We only get here if we are removing _THIS_ package
        RUN_TRIGGER="UninstallSELF"
    elif [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -eq 1 ]]; then
        # We only get here if we are NOT doing an upgrade of the trigger package
        #                and we are installing _THIS_ package for the first time
        RUN_TRIGGER="Initial"
    elif [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -gt 1 ]]; then
        # We only get here if we are NOT doing an upgrade of the trigger package
        #                and we are upgrading _THIS_ package
        RUN_TRIGGER="UpgradeSELF"
    fi
elif [[ ${TRIGGER_ON_PACKAGE} -gt 1 ]]; then
    # We only get here if we are doing an upgrade of the trigger package
    if [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -eq 1 ]]; then
        # We get here if we are doing an upgrade of the trigger package
        #                     and we are NOT upgrading _THIS_ package
        RUN_TRIGGER="UpgradeTRIGGERON"

        #  But, are we installing _THIS_ package as a part of a dependency
        #       resolution chain?
        _THIS_TID=$(rpm -q --qf "%{INSTALLTID}\n" %{NAME})
        # Find the last installed (ie the current) TRIGGER_ON_PACKAGE_NAME's transaction
        TID=$(rpm -q --qf "%{INSTALLTID}\n" ${TRIGGER_ON_PACKAGE_NAME} --last |grep -v ${TRIGGER_ON_PACKAGE_NAME} | head -1)
        if [[ "${_THIS_TID}" == "${TID}" ]]; then
            # if the transaction ID of _THIS_ package is identical to the
            #  transaction ID of an installed TRIGGER_ON_PACKAGE_NAME
            # then, we must be upgrading the trigger package and
            # installing _THIS_ package
            RUN_TRIGGER="InitialSELFUpgradeTRIGGERON"
        fi
    elif [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -gt 1 ]]; then
        # We only get here if we are doing an upgrade of the trigger package
        #                     and we are upgrading _THIS_ package
        RUN_TRIGGER="UpgradeALL"
    fi
elif [[ ${TRIGGER_ON_PACKAGE} -eq 0 ]]; then
    # We only get here if we are removing the trigger package
    RUN_TRIGGER="UninstallTRIGGERON"
fi

if [[ "${RUN_TRIGGER}" == "NO" ]]; then
    # If we got here if:
    #  some kind of edge case appeared......
    echo "##################################" >&2
    echo "%{NAME}: Not sure what this means"  >&2
    echo "CURRENT_INSTALLS_OF_THIS_PACKAGE = ${CURRENT_INSTALLS_OF_THIS_PACKAGE}"  >&2
    echo "TRIGGER_ON_PACKAGE (${TRIGGER_ON_PACKAGE_NAME}) = ${TRIGGER_ON_PACKAGE}" >&2
    echo "##################################" >&2
    exit 1
fi

##################### End of Trigger Snippet ########################

if [[ "${RUN_TRIGGER}" == "UpgradeTRIGGERON" ]]; then
    # If we got here if:
    #  a) we are upgrading the trigger package, but not _THIS_ package
    #       so we've already run this once and will not run it again.

    # If the user changed the config themselves, we shouldn't undo their work
    #  if we decide we need to, we can always alter the behavior in the next
    #  version of this package.
    exit 0
fi


# # #
# This way external scripts/config tools can call these changes if they want
%{_libexecdir}/%{name}/%{name}.sh
systemctl condrestart sshd.service

#####################################################################
%triggerun -p /bin/bash -- openssh-server

##################### BEGIN Trigger Snippet #########################
set -u
TRIGGER_ON_PACKAGE_NAME='openssh-server'
# The following script snippet attempts to classify why we were called:
#  - on first install of either package, RUN_TRIGGER == "Initial"
#  - on upgrade of _THIS_ package, RUN_TRIGGER == "UpgradeSELF"
#  - on upgrade of the TRIGGERON package, RUN_TRIGGER == "UpgradeTRIGGERON"
#  - on upgrade of the TRIGGERON package but initial install of _THIS_ package, RUN_TRIGGER == "InitialSELFUpgradeTRIGGERON"
#  - on upgrade of the BOTH packages, RUN_TRIGGER == "UPGRADEALL"

CURRENT_INSTALLS_OF_THIS_PACKAGE=${1:-0}
TRIGGER_ON_PACKAGE=${2:-0}

RUN_TRIGGER="NO"
if [[ ${TRIGGER_ON_PACKAGE} -eq 1 ]]; then
    # We only get here if we are NOT doing an upgrade of the trigger package
    if [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -eq 0 ]]; then
        # We only get here if we are removing _THIS_ package
        RUN_TRIGGER="UninstallSELF"
    elif [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -eq 1 ]]; then
        # We only get here if we are NOT doing an upgrade of the trigger package
        #                and we are installing _THIS_ package for the first time
        RUN_TRIGGER="Initial"
    elif [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -gt 1 ]]; then
        # We only get here if we are NOT doing an upgrade of the trigger package
        #                and we are upgrading _THIS_ package
        RUN_TRIGGER="UpgradeSELF"
    fi
elif [[ ${TRIGGER_ON_PACKAGE} -gt 1 ]]; then
    # We only get here if we are doing an upgrade of the trigger package
    if [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -eq 1 ]]; then
        # We get here if we are doing an upgrade of the trigger package
        #                     and we are NOT upgrading _THIS_ package
        RUN_TRIGGER="UpgradeTRIGGERON"

        #  But, are we installing _THIS_ package as a part of a dependency
        #       resolution chain?
        _THIS_TID=$(rpm -q --qf "%{INSTALLTID}\n" %{NAME})
        # Find the last installed (ie the current) TRIGGER_ON_PACKAGE_NAME's transaction
        TID=$(rpm -q --qf "%{INSTALLTID}\n" ${TRIGGER_ON_PACKAGE_NAME} --last |grep -v ${TRIGGER_ON_PACKAGE_NAME} | head -1)
        if [[ "${_THIS_TID}" == "${TID}" ]]; then
            # if the transaction ID of _THIS_ package is identical to the
            #  transaction ID of an installed TRIGGER_ON_PACKAGE_NAME
            # then, we must be upgrading the trigger package and
            # installing _THIS_ package
            RUN_TRIGGER="InitialSELFUpgradeTRIGGERON"
        fi
    elif [[ ${CURRENT_INSTALLS_OF_THIS_PACKAGE} -gt 1 ]]; then
        # We only get here if we are doing an upgrade of the trigger package
        #                     and we are upgrading _THIS_ package
        RUN_TRIGGER="UpgradeALL"
    fi
elif [[ ${TRIGGER_ON_PACKAGE} -eq 0 ]]; then
    # We only get here if we are removing the trigger package
    RUN_TRIGGER="UninstallTRIGGERON"
fi

if [[ "${RUN_TRIGGER}" == "NO" ]]; then
    # If we got here if:
    #  some kind of edge case appeared......
    echo "##################################" >&2
    echo "%{NAME}: Not sure what this means"  >&2
    echo "CURRENT_INSTALLS_OF_THIS_PACKAGE = ${CURRENT_INSTALLS_OF_THIS_PACKAGE}"  >&2
    echo "TRIGGER_ON_PACKAGE (${TRIGGER_ON_PACKAGE_NAME}) = ${TRIGGER_ON_PACKAGE}" >&2
    echo "##################################" >&2
    exit 1
fi

##################### End of Trigger Snippet ########################
if [[ "${RUN_TRIGGER}" != "UninstallSELF" ]]; then
    # If we got here if:
    #  we are not uninstalling _THIS_ package
    exit 0
fi


# # #
# This way external scripts/config tools can call these changes if they want
%{_libexecdir}/%{name}/%{name}.sh -r
systemctl condrestart sshd.service
#####################################################################
%endif

%files server
%defattr(0644,root,root,0755)
%if 0%{?rhel} >= 8 || 0%{?fedora} >= 27
%config %attr(0600,root,root) /etc/ssh/sshd_config.d/*.conf
%else
%attr(0750,root,root) %{_libexecdir}/%{name}/%{name}.sh
%endif


#####################################################################
#####################################################################
%post client -p /bin/bash
grep -q '^Include /etc/ssh/ssh_config.d/\*.conf' /etc/ssh/ssh_config
if [[ $? -ne 0 ]]; then
    echo 'Include /etc/ssh/ssh_config.d/*.conf' >> /etc/ssh/ssh_config
    %{_fixperms} /etc/ssh/ssh_config
    restorecon -F /etc/ssh/ssh_config
fi
exit 0

%files client
%defattr(0644,root,root,0755)
%config %{_sysconfdir}/ssh/ssh_config.d/fermilab_ssh-client.conf

#####################################################################
%changelog
* Wed Apr 13 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-6.1
- Use boolean conditional dependency for more rich behavior

* Tue Apr 5 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-6
- EL8.6 supports sshd includes, use those now
- New SSHD has stricter mask requirements, fix ULA mask

* Wed Mar 16 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-5
- Repackage for public with subpackages
