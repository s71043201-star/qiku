import sys, io

root = sys.argv[1]
s = io.open(root + '/index.html', encoding='utf-8', newline='').read()
bk = root + '/tools/_backup_20261117/'
old_frag = io.open(bk + 'index.html', encoding='utf-8', newline='').read()
shell = io.open(bk + 'play.html', encoding='utf-8', newline='').read()
assert shell.count(old_frag) == 1
io.open(root + '/play.html', 'w', encoding='utf-8', newline='').write(shell.replace(old_frag, s))
i1 = s.index('<script>') + 8
io.open('C:/tmp/qiku_check.js', 'w', encoding='utf-8').write(s[i1:s.rindex('</script>')])
print('ok', 'lone LF:', s.replace('\r\n', '').count('\n'), 'CRLF:', s.count('\r\n'))
