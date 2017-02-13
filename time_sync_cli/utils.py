import subprocess


def tail_file(path, follow=False, verbose=False):
    tail_cmd = ['tail']
    if follow:
        tail_cmd.append('-F')
    tail_cmd.append(path)
    f = subprocess.Popen(tail_cmd,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    print(' [*] To exit, hit CTRL+C..')
    while True:
        line = f.stdout.readline()
        if line:
            if verbose:
                print line
            else:
                if 'DEBUG' not in line:
                    print line
        else:
            if not follow:
                return
    pass
