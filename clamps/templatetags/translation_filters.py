# Copyright [2025] [OBARA (Nanjing) Electromechanical Co., Ltd]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.



from django import template

register = template.Library()

TRANSLATION_MAPPING = {
    "大型":"Large",
    "中型": "Medium",
    "小型": "Small",
    "仙鹤型": "Crane Type",
    "中小型": "Small-Medium",
    "特殊": "Special",
    "多摩川": "Tamagawa",
    "其他": "Others",
    "水平": "Horizontal",
    "竖直": "Vertical",
    "下置": "Bottom",
    "上置": "Top",
    "右置": "Right",
    "握杆（铝）": "Grip Rod (Aluminum)",
    "TIP BASE（F 型）": "TIP BASE (F Type)",
    "握杆（SBA）": "Grip Rod (SBA)",
    "TIP BASE（G 型）": "TIP BASE (G Type)",
    "GUN HEAD（?36）": "GUN HEAD (?36)",
    "GUN HEAD（?45）": "GUN HEAD (?45)",
    "GUN HEAD（?40）": "GUN HEAD (?40)",
    "GUN HEAD（?50）": "GUN HEAD (?50)",
    "GUN HEAD（?60）": "GUN HEAD (?60)",
    "握杆?45（铝）": "Grip Rod ?45 (Aluminum)",
    "握杆?50（铝）": "Grip Rod ?50 (Aluminum)",
    "有": "Yes",
    "无": "No",
    "右": "Right",
    "上": "Up",
    "前": "Front",
    "下": "Down",
    "后": "Back",
    "三维": "3D",
    "左": "Left",
    "1进1出": "1 In 1 Out",
    "2进2出": "2 In 2 Out",
    "3进3出": "3 In 3 Out",
    "1进2出": "1 In 2 Out",
    "2进3出": "2 In 2 Out",
    "1进3出": "1 In 3 Out",
    "高压": "High Pressure",
    "低压": "Low Pressure",
    "偏心": "Eccentricity",
    "中空": "Hollow",
    "联轴器型": "Coupling Type",
    "折回": "Foldback",
    "后置": "Stolpe",
    "铝": "Aluminum",
}

@register.filter(name='translate')
def translate(value):
    return TRANSLATION_MAPPING.get(value, value)


