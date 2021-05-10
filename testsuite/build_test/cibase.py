#!/usr/bin/env python3

import os
import re
import tempfile

from cibuilder import CIBuilder
from avocado.utils import process

isar_root = os.path.dirname(__file__) + '/../..'

class CIBaseTest(CIBuilder):

    def perform_build_test(self, targets, cross, bitbake_cmd):
        build_dir = self.params.get('build_dir', default=isar_root + '/build')
        quiet = int(self.params.get('quiet', default=0))
        bitbake_args = '-v'

        if quiet:
            bitbake_args = ''

        self.log.info('===================================================')
        self.log.info('Running Isar build test for:')
        self.log.info(targets)
        self.log.info('Isar build folder is: ' + build_dir)
        self.log.info('===================================================')

        self.init(build_dir)
        self.confprepare(build_dir, 1, cross, 1)

        self.log.info('Starting build...')

        self.bitbake(build_dir, targets, bitbake_cmd, bitbake_args)

    def perform_repro_test(self, targets, signed):
        build_dir = self.params.get('build_dir', default=isar_root + '/build')
        cross = int(self.params.get('cross', default=0))
        quiet = int(self.params.get('quiet', default=0))
        bitbake_args = '-v'

        if quiet:
            bitbake_args = ''

        self.log.info('===================================================')
        self.log.info('Running repro Isar build test for:')
        self.log.info(targets)
        self.log.info('Isar build folder is: ' + build_dir)
        self.log.info('===================================================')

        self.init(build_dir)
        self.confprepare(build_dir, 1, cross, 0)

        gpg_pub_key = os.path.dirname(__file__) + '/../base-apt/test_pub.key'
        gpg_priv_key = os.path.dirname(__file__) + '/../base-apt/test_priv.key'

        if signed:
            with open(build_dir + '/conf/ci_build.conf', 'a') as file:
                # Enable use of signed cached base repository
                file.write('BASE_REPO_KEY="file://' + gpg_pub_key + '"\n')

        os.chdir(build_dir)

        os.environ['GNUPGHOME'] = tempfile.mkdtemp()
        result = process.run('gpg --import %s %s' % (gpg_pub_key, gpg_priv_key))

        if result.exit_status:
            self.fail('GPG import failed')

        self.bitbake(build_dir, targets, None, bitbake_args)

        self.deletetmp(build_dir)
        with open(build_dir + '/conf/ci_build.conf', 'a') as file:
            file.write('ISAR_USE_CACHED_BASE_REPO = "1"\n')
            file.write('BB_NO_NETWORK = "1"\n')

        self.bitbake(build_dir, targets, None, bitbake_args)

        # Cleanup and disable use of signed cached base repository
        self.deletetmp(build_dir)
        self.confcleanup(build_dir)

    def perform_wic_test(self, targets, wks_path, wic_path):
        build_dir = self.params.get('build_dir', default=isar_root + '/build')
        cross = int(self.params.get('cross', default=0))
        quiet = int(self.params.get('quiet', default=0))
        bitbake_args = '-v'

        if quiet:
            bitbake_args = ''

        self.log.info('===================================================')
        self.log.info('Running WIC exclude build test for:')
        self.log.info(targets)
        self.log.info('Isar build folder is: ' + build_dir)
        self.log.info('===================================================')

        self.init(build_dir)
        self.confprepare(build_dir, 1, cross, 1)

        layerdir_isar = self.getlayerdir('isar')

        wks_file = layerdir_isar + wks_path
        wic_img = build_dir + wic_path

        if not os.path.isfile(wic_img):
            self.fail('No build started before: ' + wic_img + ' not exist')

        self.backupfile(wks_file)
        self.backupmove(wic_img)

        with open(wks_file, 'r') as file:
            lines = file.readlines()
        with open(wks_file, 'w') as file:
            for line in lines:
                file.write(re.sub(r'part \/ ', 'part \/ --exclude-path usr ',
                                  line))

        try:
            self.bitbake(build_dir, targets, None, bitbake_args)
        finally:
            self.restorefile(wks_file)

        self.restorefile(wic_img)

    def perform_container_test(self, targets, bitbake_cmd):
        build_dir = self.params.get('build_dir', default=isar_root + '/build')
        cross = int(self.params.get('cross', default=0))
        quiet = int(self.params.get('quiet', default=0))
        bitbake_args = '-v'

        if quiet:
            bitbake_args = ''

        self.log.info('===================================================')
        self.log.info('Running Isar Container test for:')
        self.log.info(targets)
        self.log.info('Isar build folder is: ' + build_dir)
        self.log.info('===================================================')

        self.init(build_dir)
        self.confprepare(build_dir, 1, cross, 1)
        self.containerprep(build_dir)

        self.bitbake(build_dir, targets, bitbake_cmd, bitbake_args)

