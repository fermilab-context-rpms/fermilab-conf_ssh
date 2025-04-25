Name:		fermilab-conf_ssh
Version:	1.2
Release:	1%{?dist}
Summary:	Configure SSH for use with Fermilab

Group:		Fermilab
License:	GPL
URL:		https://github.com/fermilab-context-rpms/fermilab-conf_ssh

BuildRequires:	coreutils
BuildArch:	noarch

Source0:	%{name}.tar.xz
Requires:	(%{name}-client == %{version}-%{release} if openssh-clients)
Requires:	(%{name}-server == %{version}-%{release} if openssh-server)

%description
The default configuration for openssh is not fully suitable for use with
Fermilab.

Behavior from: CS-doc-1186


%package client
Summary:	Add Fermilab ssh_config to %{_sysconfdir}/ssh/ssh_config.d/
Requires:	openssh-clients > 7.8
Requires(post):	policycoreutils coreutils grep
Recommends:	krb5-workstation

%description client
The default configuration for openssh-client does not take full advantage
of the expected Fermilab openssh-server settings.

This includes X11Forwarding and GSSAPI credential forwarding.

The default behavior of openssh-client includes files from %{_sysconfdir}/ssh/ssh_config.d/*.conf

Behavior from: CS-doc-1186

%package client-delegate-all
Summary:        Add rule to always delegate GSSAPI ssh_config to %{_sysconfdir}/ssh/ssh_config.d/
Requires:       openssh-clients > 7.8
Requires(post): policycoreutils coreutils grep
Recommends:     krb5-workstation

%description client-delegate-all
The Fermilab configuration for openssh-client may not forward credentials in some situations.
This package adds a setting to always delegate GSSAPI credentials to any host.

The default behavior of openssh-client includes files from %{_sysconfdir}/ssh/ssh_config.d/*.conf


%package server
Summary:	Add Fermilab sshd_config to %{_sysconfdir}/ssh/ssh_config.d/
%if 0%{?rhel} >= 9 || 0%{?fedora} >= 31
Conflicts:	openssh-server < 8.2
%else
Conflicts:	openssh-server < 8.0p1-12
%endif
Recommends:	krb5-workstation
Recommends:	openssh-server
Recommends:	xorg-x11-xauth
Recommends:	%{name}-client >= %{version}-%{release}
Suggests:	fermilab-conf_kerberos
Suggests:	fermilab-conf_timesync
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

# client-delegate-all
%{__install} -D client/fermilab_ssh-client-delegate-all.conf %{buildroot}/%{_sysconfdir}/ssh/ssh_config.d/fermilab_ssh-client-delegate-all.conf

# server
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

%files server
%defattr(0644,root,root,0755)
%config %attr(0600,root,root) /etc/ssh/sshd_config.d/*.conf


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

%files client-delegate-all
%defattr(0644,root,root,0755)
%config %{_sysconfdir}/ssh/ssh_config.d/fermilab_ssh-client-delegate-all.conf

%files
%defattr(0644,root,root,0755)


#####################################################################
%changelog
* Fri Apr 25 2025 Pat Riehecky <riehecky@fnal.gov> 1.2-1
- Add package for client-delegate-all

* Mon Oct 7 2024 Pat Riehecky <riehecky@fnal.gov> 1.1-1
- Users now need to specifically configure ExposeAuthInfo

* Mon May 9 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-7
- EL9 anaconda lets you set root login, don't override it

* Wed Apr 13 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-6.2
- Add missing toplevel package

* Wed Apr 13 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-6.1
- Use boolean conditional dependency for more rich behavior

* Tue Apr 5 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-6
- EL8.6 supports sshd includes, use those now
- New SSHD has stricter mask requirements, fix ULA mask

* Wed Mar 16 2022 Pat Riehecky <riehecky@fnal.gov> 1.0-5
- Repackage for public with subpackages
