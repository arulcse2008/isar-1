#!/usr/bin/env python3

import os
import shutil

from avocado import Test
from avocado.utils import path
from avocado.utils import process

isar_root = os.path.dirname(__file__) + '/../..'

class CIBuilder(Test):

    def init(self, build_dir):
        os.chdir(isar_root)
        output = process.getoutput('/bin/bash -c "source isar-init-build-env \
                                    %s 2>&1 >/dev/null; env"' % build_dir)
        env = dict((x.split("=", 1) for x in output.splitlines() if x != ''))
        os.environ.update(env)

    def confprepare(self, build_dir, compat_arch, cross, debsrc_cache):
        with open(build_dir + '/conf/ci_build.conf', 'w') as f:
            if compat_arch:
                f.write('ISAR_ENABLE_COMPAT_ARCH_amd64 = "1"\n')
                f.write('ISAR_ENABLE_COMPAT_ARCH_arm64 = "1"\n')
                f.write('ISAR_ENABLE_COMPAT_ARCH_debian-stretch_amd64 = "0"\n')
            if cross:
                f.write('ISAR_CROSS_COMPILE = "1"\n')
            if debsrc_cache:
                f.write('BASE_REPO_FEATURES = "cache-deb-src"\n')

        with open(build_dir + '/conf/local.conf', 'r+') as f:
            for line in f:
                if 'include ci_build.conf' in line:
                    break
            else:
                f.write('\ninclude ci_build.conf')

    def confcleanup(self, build_dir):
        open(build_dir + '/conf/ci_build.conf', 'w').close()

    def deletetmp(self, build_dir):
        process.run('rm -rf ' + build_dir + '/tmp', sudo=True)

    def bitbake(self, build_dir, target, cmd, args):
        os.chdir(build_dir)
        cmdline = ['bitbake']
        if args:
            cmdline.append(args)
        if cmd:
            cmdline.append('-c')
            cmdline.append(cmd)
        if isinstance(target, list):
            cmdline.extend(target)
        else:
            cmdline.append(target)

        process.run(" ".join(cmdline))

    def backupfile(self, path):
        shutil.copy2(path, path + '.ci-backup')

    def backupmove(self, path):
        shutil.move(path, path + '.ci-backup')

    def restorefile(self, path):
        shutil.move(path + '.ci-backup', path)

    def getlayerdir(self, layer):
        try:
            path.find_command('bitbake')
        except path.CmdNotFoundError:
            build_dir = self.params.get('build_dir',
                                        default=isar_root + '/build')
            self.init(build_dir)
        output = process.getoutput('bitbake -e | grep "^LAYERDIR_.*="')
        env = dict((x.split("=", 1) for x in output.splitlines() if x != ''))

        return env['LAYERDIR_' + layer].strip('"')

