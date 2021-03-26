class Screen():
    def __init__(self, width, height):
        self.width = int(width)
        self.height = int(height)

    def __str__(self):
        return (self.width, self.height)

    def __repr__(self):
        return '(%s, %s)' % (self.width, self.height)