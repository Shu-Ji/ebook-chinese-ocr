# coding: u8

from hashlib import md5 as _m5
from itertools import izip
import cPickle as pickle
import os
import time

from PIL import Image
import Levenshtein


md5 = lambda s: _m5(s).hexdigest()


class Otsu(object):

    FAST_VAL = 255  # 只要是非0就可以
    BINARY_THRESHOLD = 190  # 二值化阈值

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
        self.im = self.im.point(
                lambda p: p > self.BINARY_THRESHOLD and 255)  # 二值
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

        if 0 and not rotate:
            # 修正被分割的左右结构
            # 左右结构之间的间隙比较小，这里取间隙小于Npx时认为是左右结构
            N = 2
            new_starts = []
            new_ends = []
            last_s = last_e = 0

            def push(start, end):
                new_starts.append(start)
                new_ends.append(end)

            for start, end in izip(starts, ends):
                if last_s == 0:
                    push(start, end)
                elif start - last_e < N:
                    new_ends[-1] = end
                else:
                    push(start, end)

                last_s, last_e = start, end

            starts, ends = new_starts, new_ends

        i = 1
        for start, end in izip(starts, ends):
            # graph中数据是旋转90度的结果，故保存的数据对原图像来说是y轴
            if rotate:
                box = (0, start, self.w, end)
            else:
                box = (start, 0, end, self.h)
            yield self.im.crop(box), i
            i += 1


if __name__ == '__main__':
    import glob
    glob.glob('./imgs/*.jpg')
    otsu = Otsu('/home/finn/rubbish/ocr/test-10004.bmp')
    #otsu.im.show()
    i = 1000


    pickle_file = 'data.pickle'
    samples = pickle.load(open(pickle_file, 'rb'))
    bak_pickle_file = '%s._%d_%s' % (pickle_file, time.time(), '.bak')
    open(bak_pickle_file, 'wb').write(open(pickle_file, 'rb').read())

    """
    for fn in glob.glob('./cls/*.png'):
        m5, char = fn.split('.')[1].split('/')[-1].split('_')
        samples[m5] = [char, char, char]
    """

    """ replace
    m5 = '0926e148f52cb3f04cff1cb71981f28c'
    a = samples[m5]
    #a[-1] = '知-l'
    samples[m5] = a
    """

    for line, line_num in otsu.cut_to_lines():
        #line.show()
        line.save('/tmp/cut/0000000_cur_line.png')
        otsu = Otsu(im=line)
        for word, col_num in otsu.cut_to_lines(rotate=False, show=0):
            _word = word
            word = word.resize((48, 48), Image.BICUBIC).convert('1')
            data = ''.join(str(p) for p in word.getdata()).replace('255', '1')
            m5 = md5(data)
            if m5 not in samples:
                # 请开着目录/tmp/cut方便输入
                path = '/tmp/cut/%s.%s_%s.png' % (line_num, col_num, m5)
                word.save(path)

                min_distance = len(data)
                maybe = None
                for key, value in samples.items():
                    binary_string = value[-2]
                    try:
                        distance = Levenshtein.hamming(binary_string, data)
                    except:
                        del samples[key]
                    if min_distance > distance:
                        maybe = value
                        min_distance = distance
                maychar = maybe[-1]
                print 'maybe:', maychar, min_distance
                char = raw_input('input(press RETURN to accept %s):' % maychar)
                if char == '':
                    char = maychar

                os.remove(path)
                os.system('clear')
                samples[m5] = [word.tostring(), data, char]
                pickle.dump(samples, open(pickle_file, 'wb'))
                path = 'cls/%s_%s.png' % (m5, char)
                _word.save(path)
            else:
                char = samples[m5][-1]
                #samples[m5] = [word.tostring(), data, char]
                print '**:', char

            path = 'cut/%s.%s_%s_%s.png' % (line_num, col_num, m5, char)
            _word.save(path)
            i += 1
