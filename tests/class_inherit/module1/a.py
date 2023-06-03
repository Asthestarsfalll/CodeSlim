class Base(object):
    def __init__(self, name, age):
        self.name = name
        self.age = age
        self.data = {"name": self.name, "age": self.age}
        self.count = 0

    def __str__(self):
        return f"(name={self.name}, age={self.age})"

    def __len__(self):
        return len(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def __delitem__(self, key):
        del self.data[key]

    def __iter__(self):
        self.count = 0
        return self

    def __next__(self):
        if self.count < len(self.data):
            result = list(self.data.items())[self.count]
            self.count += 1
            return result
        else:
            raise StopIteration

    def __contains__(self, item):
        return item in self.data.values()

    def __add__(self, other):
        if isinstance(other, Base):
            new_name = self.name + other.name
            new_age = self.age + other.age
            return Base(new_name, new_age)
        else:
            raise TypeError(
                "unsupported operand type(s) for +: 'MyClass' and '{}'".format(
                    type(other).__name__
                )
            )

    def __eq__(self, other):
        if isinstance(other, Base):
            return self.data == other.data
        else:
            return False

    def __hash__(self):
        return hash((self.name, self.age))

    def __repr__(self):
        return f"MyClass(name={self.name!r}, age={self.age!r})"

    def method1(self):
        return "Hello, World!"

    def method2(self, x, y):
        return x + y

    def method3(self):
        return sorted(self.data.items(), key=lambda x: x[1])

    def method4(self, n):
        return [i for i in range(n) if i % 2 == 0]

    def method5(self, s):
        vowels = "aeiouAEIOU"
        return "".join([c for c in s if c not in vowels])

    def method6(self, lst):
        return [i for i in lst if i % 2 == 0]

    def method7(self, string1, string2):
        return string1.lower() == string2.lower()

    def method8(self, lst1, lst2):
        return list(set(lst1) & set(lst2))

    def method9(self, string):
        return string[::-1]

    def method10(self, string):
        return "".join(
            [c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(string)]
        )
