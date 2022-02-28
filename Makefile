_default:
	@echo "make"
sources:
	@echo "make sources"
	@tar cf - conf | xz > fermilab-conf_ssh.tar.xz
srpm: sources
	rpmbuild -bs --define '_sourcedir .' --define '_srcrpmdir .' fermilab-conf_ssh.spec
