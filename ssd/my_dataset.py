from torch.utils.data import Dataset
import os
import torch
import json
from PIL import Image
from lxml import etree


class VOC2012DataSet(Dataset):
    """读取解析PASCAL VOC2012数据集"""

    def __init__(self, voc_root, transforms, year='VOC2012', train_set='train.txt'):
        self.root = os.path.join(voc_root, "VOCdevkit", year)
        self.img_root = os.path.join(self.root, "JPEGImages")
        self.annotations_root = os.path.join(self.root, "Annotations")

        txt_list = os.path.join(self.root, "ImageSets", "Main", train_set)

        with open(txt_list) as read:
            self.xml_list = [os.path.join(self.annotations_root, line.strip() + ".xml")
                             for line in read.readlines()]

        # read class_indict
        try:
            json_file = open('./pascal_voc_classes.json', 'r')
            self.class_dict = json.load(json_file)
        except Exception as e:
            print(e)
            exit(-1)

        self.transforms = transforms

    def __len__(self):
        return len(self.xml_list)

    def __getitem__(self, idx):
        # read xml
        xml_path = self.xml_list[idx]
        with open(xml_path) as fid:
            xml_str = fid.read()
        xml = etree.fromstring(xml_str)
        data = self.parse_xml_to_dict(xml)["annotation"]
        data_height = int(data["size"]["height"])
        data_width = int(data["size"]["width"])
        height_width = [data_height, data_width]
        img_path = os.path.join(self.img_root, data["filename"])
        image = Image.open(img_path)
        if image.format != "JPEG":
            raise ValueError("Image format not JPEG")
        boxes = []
        labels = []
        iscrowd = []
        for obj in data["object"]:
            # 将所有的gt box信息转换成相对值0-1之间
            xmin = float(obj["bndbox"]["xmin"]) / data_width
            xmax = float(obj["bndbox"]["xmax"]) / data_width
            ymin = float(obj["bndbox"]["ymin"]) / data_height
            ymax = float(obj["bndbox"]["ymax"]) / data_height
            boxes.append([xmin, ymin, xmax, ymax])
            labels.append(self.class_dict[obj["name"]])
            iscrowd.append(int(obj["difficult"]))

        # convert everything into a torch.Tensor
        boxes = torch.as_tensor(boxes, dtype=torch.float32)
        labels = torch.as_tensor(labels, dtype=torch.int64)
        iscrowd = torch.as_tensor(iscrowd, dtype=torch.int64)
        height_width = torch.as_tensor(height_width, dtype=torch.int64)
        image_id = torch.tensor([idx])
        area = (boxes[:, 3] - boxes[:, 1]) * (boxes[:, 2] - boxes[:, 0])

        target = {}
        target["boxes"] = boxes
        target["labels"] = labels
        target["image_id"] = image_id
        target["area"] = area
        target["iscrowd"] = iscrowd
        target["height_width"] = height_width

        if self.transforms is not None:
            image, target = self.transforms(image, target)

        return image, target

    def get_height_and_width(self, idx):
        # read xml
        xml_path = self.xml_list[idx]
        with open(xml_path) as fid:
            xml_str = fid.read()
        xml = etree.fromstring(xml_str)
        data = self.parse_xml_to_dict(xml)["annotation"]
        data_height = int(data["size"]["height"])
        data_width = int(data["size"]["width"])
        return data_height, data_width

    def parse_xml_to_dict(self, xml):
        """
        将xml文件解析成字典形式，参考tensorflow的recursive_parse_xml_to_dict
        Args：
            xml: xml tree obtained by parsing XML file contents using lxml.etree

        Returns:
            Python dictionary holding XML contents.
        """

        if len(xml) == 0:  # 遍历到底层，直接返回tag对应的信息
            return {xml.tag: xml.text}

        result = {}
        for child in xml:
            child_result = self.parse_xml_to_dict(child)  # 递归遍历标签信息
            if child.tag != 'object':
                result[child.tag] = child_result[child.tag]
            else:
                if child.tag not in result:  # 因为object可能有多个，所以需要放入列表里
                    result[child.tag] = []
                result[child.tag].append(child_result[child.tag])
        return {xml.tag: result}


# import transforms
# from draw_box_utils import draw_box
# from PIL import Image
# import json
# import matplotlib.pyplot as plt
# import torchvision.transforms as ts
# import random
#
# # read class_indict
# category_index = {}
# try:
#     json_file = open('./pascal_voc_classes.json', 'r')
#     class_dict = json.load(json_file)
#     category_index = {v: k for k, v in class_dict.items()}
# except Exception as e:
#     print(e)
#     exit(-1)
#
# data_transform = {
#     "train": transforms.Compose([transforms.ToTensor(),
#                                  transforms.RandomHorizontalFlip(0.5)]),
#     "val": transforms.Compose([transforms.ToTensor()])
# }
#
# # load train data set
# train_data_set = VOC2012DataSet(os.getcwd(), data_transform["train"], True)
# print(len(train_data_set))
# for index in random.sample(range(0, len(train_data_set)), k=5):
#     img, target = train_data_set[index]
#     img = ts.ToPILImage()(img)
#     draw_box(img,
#              target["boxes"].numpy(),
#              target["labels"].numpy(),
#              [1 for i in range(len(target["labels"].numpy()))],
#              category_index,
#              thresh=0.5,
#              line_thickness=5)
#     plt.imshow(img)
#     plt.show()
