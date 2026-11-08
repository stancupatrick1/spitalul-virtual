import pcbnew, sys, re, collections
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.WriteDRCReport(b, sys.argv[2], pcbnew.EDA_UNITS_MILLIMETRES, True)
t = open(sys.argv[2]).read()
c = collections.Counter(re.findall(r'^\[(\w+)\]', t, re.M))
for k, v in c.most_common(): print(v, k)
