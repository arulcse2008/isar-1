#
# Copyright (c) Siemens AG, 2018
#
# SPDX-License-Identifier: MIT
#
# DESCRIPTION
# This implements the 'rootfs-u-boot' source plugin class for 'wic'.
# It performs the same tasks as the 'rootfs' plugin and additionally configures
# u-boot-script to boot this rootfs.
# Recognized sourceparams:
#  - no_initrd=yes          (disables initrd loading)
#  - overlays=file.dtbo ... (overlay files)
#  - builtin_dt=no          (use DT from uboot instead of kernel)
#  - script_prepend=cmd;... (prepends U-Boot command)

import glob
import logging
import re
import os

from wic import WicError
from wic.plugins.source.rootfs import RootfsPlugin
from wic.misc import exec_cmd

logger = logging.getLogger('wic')

class RootfsUBootPlugin(RootfsPlugin):
    """
    Populate partition content from a rootfs directory and set up
    /etc/default/u-boot-script.
    """

    name = 'rootfs-u-boot'

    @classmethod
    def do_prepare_partition(cls, part, source_params, cr, cr_workdir,
                             oe_builddir, bootimg_dir, kernel_dir,
                             krootfs_dir, native_sysroot):
        # Prologue from RootfsPlugin.do_prepare_partition, retrieves the
        # rootfs directory
        if part.rootfs_dir is None:
            if not 'ROOTFS_DIR' in krootfs_dir:
                raise WicError("Couldn't find --rootfs-dir, exiting")

            rootfs_dir = krootfs_dir['ROOTFS_DIR']
        else:
            if part.rootfs_dir in krootfs_dir:
                rootfs_dir = krootfs_dir[part.rootfs_dir]
            elif part.rootfs_dir:
                rootfs_dir = part.rootfs_dir
            else:
                raise WicError("Couldn't find --rootfs-dir=%s connection or "
                               "it is not a valid path, exiting" % part.rootfs_dir)
        if os.path.isdir(rootfs_dir):
            real_rootfs_dir = rootfs_dir
        else:
            image_rootfs_dir = get_bitbake_var("IMAGE_ROOTFS", rootfs_dir)
            if not os.path.isdir(image_rootfs_dir):
                raise WicError("No valid artifact IMAGE_ROOTFS from image "
                               "named %s has been found at %s, exiting." %
                               (rootfs_dir, image_rootfs_dir))
            real_rootfs_dir = image_rootfs_dir

        root_dev = cr.rootdev
        if not root_dev:
            root_dev = source_params.get("root", None)
            if not root_dev:
                raise WicError("root not defined, exiting.")
            root_dev = root_dev.replace(":", "=")

        u_boot_script = os.path.join(real_rootfs_dir,
                                     "etc/default/u-boot-script")
        if not os.path.exists(u_boot_script):
            raise WicError("u-boot-script package not installed")

        # Write new /etc/default/u-boot-script
        with open(u_boot_script, 'w') as cfg:
            cfg.write('# Generated by wic, rootfs-u-boot plugin\n')
            cfg.write('ROOT_PARTITION="%d"\n' % part.realnum)
            cfg.write('KERNEL_ARGS="root=%s %s"\n' % \
                (root_dev, cr.ks.bootloader.append or ""))
            no_initrd = source_params.get('no_initrd') or ''
            cfg.write('NO_INITRD="%s"\n' % no_initrd)
            overlays = source_params.get('overlays') or ''
            cfg.write('OVERLAYS="%s"\n' % overlays)
            builtin_dt = source_params.get('builtin_dt') or ''
            cfg.write('BUILTIN_DT="%s"\n' % builtin_dt)
            script_prepend = source_params.get('script_prepend') or ''
            # remove escapes from $\{var\} that are needed to avoid expansion by wic
            script_prepend = re.sub(r'\$\\{([^\\]+)\\}', r'${\1}', script_prepend)
            # escape any quotes that aren't escaped yet
            script_prepend = re.sub(r'([^\\])"', r'\1\\"', script_prepend)
            # escape any dollars that aren't escaped yet
            script_prepend = re.sub(r'([^\\])\$', r'\1\\$', script_prepend)
            cfg.write('SCRIPT_PREPEND="%s"\n' % script_prepend)

        # Run update-u-boot-script in the target rootfs
        results = glob.glob(os.path.join("/usr/bin/qemu-*-static"))
        qemu_static = results[0] if len(results) > 0 else None
        if qemu_static:
            cp_cmd = "cp -L %s %s/usr/bin" % (qemu_static, real_rootfs_dir)
            exec_cmd(cp_cmd)
        update_cmd = "chroot %s sh -c update-u-boot-script" % real_rootfs_dir
        exec_cmd(update_cmd)
        if qemu_static:
            rm_cmd = "rm -f %s/usr/bin/%s" % (real_rootfs_dir, qemu_static)
            exec_cmd(rm_cmd)

        # For reproducibility set the time stamp of newly updated files
        if os.getenv('SOURCE_DATE_EPOCH'):
            sde_time = int(os.getenv('SOURCE_DATE_EPOCH'))
            os.utime(u_boot_script, (sde_time, sde_time))
            os.utime(os.path.join(real_rootfs_dir, "boot/boot.scr"),
                     (sde_time, sde_time))
            os.utime(os.path.join(real_rootfs_dir, "tmp"),
                     (sde_time, sde_time))

        RootfsPlugin.do_prepare_partition(part, source_params, cr, cr_workdir,
                                          oe_builddir, bootimg_dir, kernel_dir,
                                          krootfs_dir, native_sysroot)
