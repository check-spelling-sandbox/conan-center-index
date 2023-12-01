from conans import ConanFile, tools
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch"

    def test(self):
        self.run("b2 -v", run_environment=True)
