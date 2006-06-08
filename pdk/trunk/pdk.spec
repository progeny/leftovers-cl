Summary: Componentized Linux Platform Development Kit (PDK)
Name: pdk
%define version 0.0.36
Version: %{version}
Release: 1
License: GPL
Group: Development/Tools
URL: http://componentizedlinux.org/index.php/Main_Page
Source: http://archive.progeny.com/progeny/pdk/pool/main/p/pdk/pdk_%{version}.tar.gz
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root
Requires: python
BuildRequires: python, python-devel, funnelweb

%description
Simply put, Componentized Linux is a platform for building
specialized Linux distributions. Componentized Linux provides
developers with a set of reusable building blocks, called
components, which can be easily assembled into a wide variety
of configurations and customized as necessary. It combines
this componentized platform with a set of technologies
(covering installation, software management, and hardware detection,
with more on the way) that span traditional distribution boundaries
and transform the assembled components into a complete distribution.

This package contains the Componentized Linux Platform Development
Kit (PDK). Essentially, you can think of the PDK as "version
control for distributions"--it's intended to be a full suite of
tools for building and maintaining a CL-based distribution,
from assembling a full distro from a set of pre-built components
to managing the evolution of the distro over time to incorporate
upstream changes to building your own custom components to
specifying global configuration like branding to integrating
distro-specific patches and managing the changes over time.

%prep
%setup


%build
python setup.py build_ext


%install
rm -rf %{buildroot}
python setup.py install --root=%{buildroot}
sh run_atest -d
tar c --exclude=atest/packages --exclude=.svn atest \
    run_atest utest.py doc/*.fw >atest.tar

%clean
rm -rf %{buildroot} %{_builddir}/*


%files
%defattr(-, root, root, 0755)
%doc atest.tar doc/ README
%{_bindir}/*
%{_libdir}/python?.?/site-packages/pdk
%{_libdir}/python?.?/site-packages/picax
%{_libdir}/python?.?/site-packages/hashfile.py*


%changelog
* Thu Jun 8 2006 Darrin Thompson <darrint@progeny.com> - 0.0.36-1
- Make receiving a push more reliable.

* Wed May 25 2006 Darrin Thompson <darrint@progeny.com> - 0.0.35-1
- Make pdk work over https and Basic Auth.
- Expose find_upgrade and find_newest to api.

* Thu May 11 2006 Darrin Thompson <darrint@progeny.com> - 0.0.34-1
- Some api changes to support Progney internal projects.
- Fix upgrade bug, where sometimes downgrades happened.

* Fri May 5 2006 Darrin Thompson <darrint@progeny.com> - 0.0.33-1
- Fix bugs affecting RPM distros.
- Fix bug where entities weren't preserved when writing components.

* Fri Apr 21 2006 Darrin Thompson <darrint@progeny.com> - 0.0.32-1
- Initial rpm release.
- Incorporate changes needed to run pdk and tests in CentOS 4
- Original spec file via twisted packaging from Jeremy Katz.
