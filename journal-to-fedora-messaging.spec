# Many of the test requirements are not in epel9 yet
%if 0%{?rhel} && 0%{?rhel} <= 9
%bcond_with tests
%else
%bcond_without tests
%endif

Name:           journal-to-fedora-messaging
Version:        0.1.0
Release:        %autorelease
Summary:        Relay journal entries to Fedora Messaging
License:        GPL-3.0-or-later
URL:            https://github.com/fedora-infra/journal-to-fedora-messaging
Source0:        %{pypi_source %{name}}
Source1:        sysuser.conf

BuildArch:      noarch

BuildRequires:  python%{python3_pkgversion}-devel
# https://docs.fedoraproject.org/en-US/packaging-guidelines/UsersAndGroups/
BuildRequires:  systemd-rpm-macros
%{?sysusers_requires_compat}

%if %{with tests}
# Test dependencies
BuildRequires:  python3-pytest
BuildRequires:  python3-pytest-cov
BuildRequires:  python3-pytest-twisted
%endif

%description
This application relays messages coming from systemd's journal to Fedora Messaging.


%prep
%autosetup -p1

%generate_buildrequires
%pyproject_buildrequires

%build
%pyproject_wheel

%install
%pyproject_install
%pyproject_save_files journal_to_fedora_messaging
install -p -D -m 0644 %{SOURCE1} %{buildroot}%{_sysusersdir}/%{name}.conf


%check
%if %{with tests}
%{__python3} -m pytest tests
%endif


%pre
%sysusers_create_compat %{SOURCE1}


%files -f %{pyproject_files}
%{!?_licensedir:%global license %%doc}
%license LICENSES/*
%doc README.md *.example *.service
%{_bindir}/%{name}
%{_sysusersdir}/%{name}.conf


%changelog
%autochangelog
