find . -name "*.pyc" -o -name "*.pyo" -o -name "*~" \
    -o -name "*.snap.tar.gz" -o -name "*.html" | xargs -r rm -f
rm -rf build/
rm -rf atest.log.d
rm -f atest.log future.log
[ -e debian/files ] && fakeroot ./debian/rules clean || true

