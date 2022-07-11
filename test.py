__author__ = 'lWX351640'
def fun1():
    return[lambda x:i*x for i in range(4)]
print([m(2) for m in fun1()])
print(fun1())
