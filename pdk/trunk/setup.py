from distutils.core import setup

# Install pdk.test for now, so that pylint will automatically
# check the unit tests also.

# In the future we may want to leave pdk.test out of this, as it
# isn't actually needed at runtime.

setup(name="pdk",
      scripts=["bin/pdk"],
      packages=["pdk", "pdk.test"])

