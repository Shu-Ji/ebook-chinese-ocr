# coding: u8

from itertools import izip

from PIL import Image


class Otsu(object):

    FAST_VAL = 255

    def __init__(self, path=None, im=None):
        if im is None:
            self.open_image(path)
        else:
            self.im = im
        self.w, self.h = self.im.size

    def get_vertical_projection(self, fast=True, rotate=False):
        u'''得到二值图像的垂直投影图。

        返回包含投影数据的列表，列表中的数字表示某列所有像素值为0的个数。

        如果fast为True，那么当某列已经有字符，就不再继续查找此列了。
        注意：此时返回的graph中的值为0或FAST_VAL，并不是总个数。

        '''

        im = self.im.transpose(Image.ROTATE_90) if rotate else self.im
        pixels = im.load()
        w, h = im.size
        graph = [0] * w
        for x in range(w):
            for y in range(h):
                pixel = pixels[x, y]
                if pixel == 0:  # 此列有字符
                    if fast:  # 跳过此列
                        graph[x] = self.FAST_VAL
                        break
                    else:
                        graph[x] += 1
        return graph

    def show_vertical_projection(self, graph):
        w = len(graph)
        h = max(graph)
        img = Image.new('1', (w, h))
        for x in range(w):
            for y in range(h):
                if y <= graph[x]:
                    img.putpixel((x, y), 255)
                else:
                    break
        # 图是从左上角画的，为了方便查看，将其头尾旋转
        img.transpose(Image.FLIP_TOP_BOTTOM).show()
        return self

    def open_image(self, path):
        im = Image.open(path)
        self.im = im.convert('L')  # 灰度
        self.im = self.im.point(lambda p: p > 150 and 255)  # 二值
        return self

    def cut_to_lines(self, rotate=True, show=False):
        u"""将二值图片按行切割。

        原理：按照图片旋转90度后的垂直投影图切割。
        """

        graph = self.get_vertical_projection(fast=True, rotate=rotate)
        if show:
            self.show_vertical_projection(graph)

        if len(list(set(graph))) == 1:  # 数字全为0，表示没有任何文字
            return

        starts = []  # 保存所有FAST_VAL元素在每行中第一次出现的index
        ends = []  # 保存所有FAST_VAL元素在每行中最后一次出现的index
        # 若graph = [0, 0, 255, 255, 255, 0, 0, 0, 255, 255, 0, 255, 0, 0]
        #                   |         |             |    |     /  \
        # 则starts == [     2,        4,            8,   9,   11, 11]
        char = self.FAST_VAL  # 找FAST_VAL
        for i, v in enumerate(graph):
            if v == char:
                # 交换查找项
                if char == self.FAST_VAL:  # 找到当前行的第一个FAST_VAL
                    char = 0
                    starts.append(i)
                else:  # 找到当前行的最后一个FAST_VAL
                    char = self.FAST_VAL
                    ends.append(i - 1)  # i为0的位置，i-1则为FAST_VAL的位置

        print starts, ends
        for start, end in izip(starts, ends):
            # graph中数据是旋转90度的结果，故保存的数据对原图像来说是y轴
            if rotate:
                box = (0, start, self.w, end)
            else:
                box = (start, 0, end, self.h)
            yield self.im.crop(box)


if __name__ == '__main__':
    otsu = Otsu('./imgs/test-11.jpg')
    first_line = list(otsu.cut_to_lines())[-1]
    #first_line.show()
    otsu = Otsu(im=first_line)
    i = 10
    for word in otsu.cut_to_lines(rotate=False):
        path = 'cut/%s.jpg' % i
        #word.show(path)
        word.save(path)
        i += 1
        pass
