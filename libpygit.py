import os
import re
import sys
import zlib
import grp
import pwd
import hashlib
import argparse
import configparser
from math import ceil
from fnmatch import fnmatch
from datetime import datetime

arg_parser = argparse.ArgumentParser(description='最简单的内容跟踪器')

arg_subparsers = arg_parser.add_subparsers(title='Commands', dest='command')
arg_subparsers.required = True


def main(argv=sys.argv[1:]):
    args = arg_parser.parse_args(argv)
    match args.command:
        case 'add':
            cmd_add(args)
        case 'cat-file':
            cmd_cat_file(args)
        case 'check-ignore':
            cmd_check_ignore(args)
        case 'checkout':
            cmd_checkout(args)
        case 'commit':
            cmd_commit(args)
        case 'hash-object':
            cmd_hash_object(args)
        case 'init':
            cmd_init(args)
        case 'log':
            cmd_log(args)
        case 'ls-files':
            cmd_ls_files(args)
        case 'ls-tree':
            cmd_ls_tree(args)
        case 'rev-parse':
            cmd_rev_parse(args)
        case 'rm':
            cmd_rm(args)
        case 'show-ref':
            cmd_show_ref(args)
        case 'status':
            cmd_status(args)
        case 'tag':
            cmd_tag(args)
        case _:
            print('无效命令。')


class GitRepository:
    """ 一个 Git 仓库
    """

    worktree = None
    gitdir = None
    conf = None

    def __init__(self, path, force=False):
        self.worktree = path
        self.gitdir = os.path.join(path, '.git')

        if not (force or os.path.isdir(self.gitdir)):
            raise Exception('Not a Git repository %s' % path)

        # 读取 .git/config 中的配置文件
        self.conf = configparser.ConfigParser()
        cf = repo_file(self, 'config')

        if cf and os.path.exists(cf):
            self.conf.read([cf])
        elif not force:
            raise Exception('Configuration file missing')

        if not force:
            vers = int(self.conf.get('core', 'repositoryformatversion'))
            if vers != 0:
                raise Exception('Unsupported repositoryformatversion %s' % vers)


def repo_path(repo, *path):
    """计算 repo 的 gitdir 下的路径
    """
    return os.path.join(repo.gitdir, *path)


def repo_file(repo, *path, mkdir=False):
    """与 repo_path 相同，但如果路径中某些目录不存在则会创建。
    例如, repo_file(r, "refs", "remotes", "origin", "HEAD")
    将会创建 .git/refs/remotes/origin
    """
    if repo_dir(repo, *path[:-1], mkdir=mkdir):
        return repo_path(repo, *path)


def repo_dir(repo, *path, mkdir=False):
    """与 repo_path 函数一样 但如果 mkdir 为 False 创建 path 指定的文件夹
    """
    path = repo_path(repo, *path)

    if os.path.exists(path):
        if os.path.isdir(path):
            return path
        else:
            raise Exception('Not a directory %s' % path)

    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None


def repo_create(path):
    """创建给定路径的一个新 repo
    """

    repo = GitRepository(path, force=True)

    # First, we make sure the path either doesn't exist or is an empty dir.
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception('%s is not a directory' % path)
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception('%s is not empty!' % path)
    else:
        os.makedirs(repo.worktree)

    assert repo_dir(repo, "branches", mkdir=True)
    assert repo_dir(repo, "objects", mkdir=True)
    assert repo_dir(repo, "refs", "tags", mkdir=True)
    assert repo_dir(repo, "refs", "heads", mkdir=True)

    # .git/description
    with open(repo_file(repo, 'description'), 'w') as f:
        f.write("Unnamed repository; edit this file 'description' to name the repository.\n")

    # .git/HEAD
    with open(repo_file(repo, 'HEAD'), 'w') as f:
        f.write("ref: refs/heads/master\n")

    with open(repo_file(repo, "config"), "w") as f:
        config = repo_default_config()
        config.write(f)

    return repo


def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section('core')
    ret.set('core', 'repositoryformatversion', '0')
    ret.set('core', 'filemode', 'false')
    ret.set('core', 'bare', 'false')

    return ret


argsp = arg_subparsers.add_parser("init", help="初始化一个新的空仓库。")
argsp.add_argument("path",
                   metavar="directory",
                   nargs="?",
                   default=".",
                   help="仓库创建的路径。")


def cmd_init(args):
    repo_create(args.path)


def repo_find(path='.', required=True):
    """ 识别当前路径是否是一个 repo
    """
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, '.git')):
        return GitRepository(path)

    # 如果没有返回, 递归查找父目录
    parent = os.path.realpath(os.path.join(path, '..'))

    if parent == path:
        if required:
            raise Exception('Not a Git dir')
        else:
            return None

    # 递归情况
    return repo_find(parent, required)
