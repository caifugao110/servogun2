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



from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import enum

# 定义一些常用的可选项枚举类
class ElectrodeArmEndChoices(enum.Enum):
    GRIP_ALUMINUM = "握杆（铝）"
    TIP_BASE_F = "TIP BASE（F 型）"
    GRIP_SBA = "握杆（SBA）"
    TIP_BASE_G = "TIP BASE（G 型）"
    GUN_HEAD_36 = "GUN HEAD（?36）"
    GUN_HEAD_45 = "GUN HEAD（?45）"
    GUN_HEAD_40 = "GUN HEAD（?40）"
    GUN_HEAD_50 = "GUN HEAD（?50）"
    GUN_HEAD_60 = "GUN HEAD（?60）"
    GRIP_45_ALUMINUM = "握杆?45（铝）"
    GRIP_50_ALUMINUM = "握杆?50（铝）"
    SPECIAL = "特殊"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class ElectrodeArmTypeChoices(enum.Enum):
    WELDING = "焊接"
    PROFILE = "型材"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class TransformerChoices(enum.Enum):
    ITS85 = "ITS85"
    DB6_100R1 = "DB6-100R1"
    RT552 = "RT552"
    RT752 = "RT752"
    BOSCH = "BOSCH"
    SHANGKE = "商科"
    RT906 = "RT906"
    RT706 = "RT706"
    NI110 = "NI110"
    RT452 = "RT452"
    DB6_90_510 = "DB6-90-510"
    DB6 = "DB6"
    DB6_90 = "DB6-90"
    SMF_100 = "SMF-100"
    MF_100 = "MF-100"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class TransformerPlacementChoices(enum.Enum):
    HORIZONTAL = "水平"
    VERTICAL = "竖直"
    BOTTOM = "下置"
    TOP = "上置"
    RIGHT = "右置"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class FlangePCDChoices(enum.Enum):
    PCD_125 = "125"
    PCD_125_160 = "125-160"
    PCD_160 = "160"
    PCD_200 = "200"
    PCD_92 = "92"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class BracketDirectionChoices(enum.Enum):
    RIGHT = "右"
    UP = "上"
    FRONT = "前"
    DOWN = "下"
    BACK = "后"
    THREE_DIMENSIONAL = "三维"
    LEFT = "左"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class MotorManufacturerChoices(enum.Enum):
    FANUC = "FANUC"
    KUKA = "KUKA"
    YASKAWA = "YASKAWA"
    ABB = "ABB"
    TOLOMATIC = "TOLOMATIC"
    TAMAGAWA = "多摩川"
    PANASONIC = "PANASONIC"
    DIAKONT = "DIAKONT"
    SEW = "SEW"
    SANYO = "SANYO"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class GearboxTypeChoices(enum.Enum):
    LOW_PRESSURE = "低压"
    HIGH_PRESSURE = "高压"
    COUPLING = "联轴器型"
    HOLLOW = "中空"
    TOLOMATIC = "TOLOMATIC"
    ECCENTRIC = "偏心"
    FOLD_BACK = "折回"
    OBARA_HOLLOW = "OBARA-中空"
    DIAKONT = "DIAKONT"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class BracketMaterialChoices(enum.Enum):
    ALUMINUM = "铝"
    SS400 = "SS400"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class ToolChangerChoices(enum.Enum):
    NONE = "无"
    HAS = "有"
    STAUBLI = "STAUBLI"
    NITTA = "NITTA"
    ATI_QC210 = "ATI-QC210"
    ATI_QC310 = "ATI-QC310"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class HasBalanceChoices(enum.Enum):
    HAS = "有"
    NONE = "无"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class WaterCircuitChoices(enum.Enum):
    IN1_OUT1 = "1进1出"
    IN2_OUT2 = "2进2出"
    IN3_OUT3 = "3进3出"
    IN1_OUT2 = "1进2出"
    IN2_OUT3 = "2进3出"
    IN1_OUT3 = "1进3出"
    OTHER = "其他"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class EccentricityDirectionChoices(enum.Enum):
    UP = "上"
    DOWN = "下"
    LEFT = "左"
    RIGHT = "右"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class EccentricityToCenterChoices(enum.Enum):
    YES = "是"
    NO = "否"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class GuidanceMethodChoices(enum.Enum):
    SLIDE_RAIL = "滑轨"
    GUIDE_ROD = "导杆"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]

class ProductSubCategoryTypeChoices(enum.Enum):
    LARGE = "大型"
    SPECIAL = "特殊"
    CRANE = "仙鹤型"
    MEDIUM_SMALL = "中小型"
    SMALL = "小型"
    MEDIUM = "中型"
    X_TYPE = "X"
    Y_TYPE = "Y"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分类名称")
    parent_category = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children", verbose_name="父级分类")
    description = models.TextField(null=True, blank=True, verbose_name="分类描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        verbose_name = "焊钳分类"
        verbose_name_plural = "焊钳分类"

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", verbose_name="所属分类")
    description = models.TextField(null=True, blank=True, verbose_name="描述")
    drawing_no_1 = models.CharField(max_length=255, null=True, blank=True, verbose_name="图号1(o)")
    sub_category_type = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=ProductSubCategoryTypeChoices.choices(), 
        verbose_name="产品子分类类型"
    )

    # 通用参数
    stroke = models.FloatField(null=True, blank=True, verbose_name="行程")
    electrode_arm_end = models.CharField(
        max_length=255, null=True, blank=True, 
        choices=ElectrodeArmEndChoices.choices(), 
        verbose_name="电极臂端部"
    )
    clamping_force = models.FloatField(null=True, blank=True, verbose_name="加压力")
    electrode_arm_type = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=ElectrodeArmTypeChoices.choices(), 
        verbose_name="电极臂"
    )
    transformer = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=TransformerChoices.choices(), 
        verbose_name="变压器"
    )
    weight = models.FloatField(null=True, blank=True, verbose_name="重量")
    transformer_placement = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=TransformerPlacementChoices.choices(), 
        verbose_name="变压器放置方向"
    )
    flange_pcd = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=FlangePCDChoices.choices(), 
        verbose_name="法兰P.C.D"
    )
    bracket_direction = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=BracketDirectionChoices.choices(), 
        verbose_name="托架方向"
    )
    bracket_angle = models.FloatField(null=True, blank=True, verbose_name="托架角度")
    motor_manufacturer = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=MotorManufacturerChoices.choices(), 
        verbose_name="MOTOR厂家"
    )
    bracket_count = models.FloatField(null=True, blank=True, verbose_name="托架个数")
    gearbox_type = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=GearboxTypeChoices.choices(), 
        verbose_name="齿轮箱型式"
    )
    bracket_material = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=BracketMaterialChoices.choices(), 
        verbose_name="托架材料"
    )
    gearbox_stroke = models.CharField(max_length=100, null=True, blank=True, verbose_name="齿轮箱行程")
    tool_changer = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=ToolChangerChoices.choices(), 
        verbose_name="换枪装置"
    )
    throat_depth = models.FloatField(null=True, blank=True, verbose_name="喉深")
    has_balance = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=HasBalanceChoices.choices(), 
        verbose_name="有无平衡"
    )
    throat_width = models.FloatField(null=True, blank=True, verbose_name="喉宽")
    water_circuit = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=WaterCircuitChoices.choices(), 
        verbose_name="水路"
    )

    # X2C-C 独有参数
    grip_extension_length = models.FloatField(null=True, blank=True, verbose_name="握杆伸出长度")

    # 偏心相关参数
    eccentricity = models.FloatField(null=True, blank=True, verbose_name="偏心距离")
    eccentricity_direction = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=EccentricityDirectionChoices.choices(), 
        verbose_name="偏心方向"
    )
    eccentricity_to_center = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=EccentricityToCenterChoices.choices(), 
        verbose_name="偏心是否回到中心面"
    )

    # 导向方式
    guidance_method = models.CharField(
        max_length=100, null=True, blank=True, 
        choices=GuidanceMethodChoices.choices(), 
        verbose_name="导向方式"
    )

    # X型分类独有参数
    static_arm_eccentricity = models.FloatField(null=True, blank=True, verbose_name="静臂偏心")
    static_electrode_arm_end = models.CharField(
        max_length=255, null=True, blank=True, 
        choices=ElectrodeArmEndChoices.choices(), 
        verbose_name="静电极臂端部"
    )
    moving_arm_eccentricity = models.FloatField(null=True, blank=True, verbose_name="动臂偏心")
    moving_electrode_arm_end = models.CharField(
        max_length=255, null=True, blank=True, 
        choices=ElectrodeArmEndChoices.choices(), 
        verbose_name="动电极臂端部"
    )
    pivot_to_drive_center_dist = models.FloatField(null=True, blank=True, verbose_name="支轴到驱动中心距离")
    static_arm_front_length = models.FloatField(null=True, blank=True, verbose_name="静电极臂前部长")
    static_arm_front_height = models.FloatField(null=True, blank=True, verbose_name="静电极臂前部高")
    moving_arm_front_length = models.FloatField(null=True, blank=True, verbose_name="动电极臂前部长")
    moving_arm_front_height = models.FloatField(null=True, blank=True, verbose_name="动电极臂前部高")

    # 文件路径
    pdf_file_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="PDF文件路径")
    step_file_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="STEP文件路径")
    bmp_file_path = models.CharField(max_length=255, null=True, blank=True, verbose_name="BMP文件路径")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        verbose_name = "焊钳产品"
        verbose_name_plural = "焊钳产品"
        indexes = [
            models.Index(fields=['drawing_no_1']),
            models.Index(fields=['category']),
            models.Index(fields=['sub_category_type']),
            models.Index(fields=['transformer']),
            models.Index(fields=['motor_manufacturer']),
            models.Index(fields=['has_balance']),
            models.Index(fields=['water_circuit']),
        ]

    def __str__(self):
        return f"{self.drawing_no_1 or '未知图号'} - {self.description or '无描述'}"


class Log(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="操作用户")
    action_type = models.CharField(max_length=100, verbose_name="操作类型")
    details = models.TextField(null=True, blank=True, verbose_name="操作详情")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="操作时间")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP地址")
    user_agent = models.CharField(max_length=500, null=True, blank=True, verbose_name="用户代理")
    path = models.CharField(max_length=255, null=True, blank=True, verbose_name="访问路径")
    method = models.CharField(max_length=10, null=True, blank=True, verbose_name="HTTP方法")

    class Meta:
        verbose_name = "操作日志"
        verbose_name_plural = "操作日志"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp}: {self.user or '匿名'} - {self.action_type}"


class UserProfile(models.Model):
    """用户配置模型，用于存储用户的额外配置信息"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile", verbose_name="用户")
    customer_name = models.CharField(
        max_length=255, null=True, blank=True, 
        verbose_name="客户名称", help_text="用于备注客户名称"
    )
    
    password_validity_days = models.IntegerField(
        default=5, 
        verbose_name="密码有效期（天）",
        help_text="设置为0表示永久有效，1-15表示有效天数"
    )
    password_last_changed = models.DateTimeField(
        default=timezone.now, verbose_name="密码最后修改时间"
    )
    
    max_single_download_mb = models.IntegerField(
        default=100, verbose_name="单次最大下载大小（MB）"
    )
    max_daily_download_gb = models.IntegerField(
        default=10, verbose_name="每日最大下载大小（GB）"
    )
    max_daily_download_count = models.IntegerField(
        default=100, verbose_name="每日最大下载文件数"
    )
    max_batch_download_mb = models.IntegerField(
        default=200, verbose_name="单次批量下载最大大小（MB）"
    )
    
    daily_download_size_mb = models.IntegerField(
        default=0, verbose_name="当日已下载大小（MB）"
    )
    daily_download_count = models.IntegerField(
        default=0, verbose_name="当日已下载文件数"
    )
    last_download_date = models.DateField(
        null=True, blank=True, verbose_name="最后下载日期"
    )
    
    # 添加创建者字段
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users', verbose_name='创建者')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "用户配置"
        verbose_name_plural = "用户配置"
    
    def __str__(self):
        return f"{self.user.username} 的配置"
    
    @classmethod
    def get_password_validity_choices(cls):
        """获取密码有效期选择项"""
        choices = []
        # 添加1-15天的选项
        for i in range(1, 16):
            choices.append((i, f"{i}天"))
        # 添加永久有效选项
        choices.append((0, "永久有效"))
        return choices
    
    def is_password_expired(self):
        """检查密码是否已过期"""
        if self.password_validity_days == 0:  # 永久有效
            return False
        
        from datetime import timedelta
        expiry_date = self.password_last_changed + timedelta(days=self.password_validity_days)
        return timezone.now() > expiry_date

    def get_password_expiry_date(self):
        """获取密码过期时间（返回datetime对象以便模板转换时区）"""
        if self.password_validity_days == 0:
            return "永久有效"
        # 返回datetime对象而非字符串，保留时区信息
        return self.password_last_changed + timedelta(days=self.password_validity_days)
    
    def reset_daily_download_stats(self):
        """重置每日下载统计"""
        self.daily_download_size_mb = 0
        self.daily_download_count = 0
        self.last_download_date = timezone.localtime(timezone.now()).date()
        self.save()
    
    def can_download_file(self, file_size_mb, is_batch=False, is_english=False):
        """检查是否可以下载指定大小的文件"""
        today = timezone.localtime(timezone.now()).date()
        
        # 如果是新的一天，重置统计
        if self.last_download_date != today:
            self.reset_daily_download_stats()
        
        # 设置单次下载大小限制，批量下载使用专门的限制
        if is_batch:
            max_single_download = self.max_batch_download_mb
        else:
            max_single_download = self.max_single_download_mb
        
        # 检查单次下载大小限制
        if file_size_mb > max_single_download:
            if is_english:
                return False, f"File size exceeds {'batch' if is_batch else 'single'} download limit ({max_single_download}MB)"
            else:
                return False, f"文件大小超过{'批量' if is_batch else '单次'}下载限制（{max_single_download}MB）"
        
        # 检查每日下载大小限制
        if (self.daily_download_size_mb + file_size_mb) > (self.max_daily_download_gb * 1024):
            if is_english:
                return False, f"Today's download will exceed the limit ({self.max_daily_download_gb}GB)"
            else:
                return False, f"今日下载量将超过限制（{self.max_daily_download_gb}GB）"
        
        # 检查每日下载次数限制
        if self.daily_download_count >= self.max_daily_download_count:
            if is_english:
                return False, f"Today's download count has reached the limit ({self.max_daily_download_count} files)"
            else:
                return False, f"今日下载文件数已达到限制（{self.max_daily_download_count}个）"
        
        if is_english:
            return True, "Can download"
        else:
            return True, "可以下载"
    
    def record_download(self, file_size_mb):
        """记录下载行为"""
        today = timezone.localtime(timezone.now()).date()
        
        # 如果是新的一天，重置统计
        if self.last_download_date != today:
            self.reset_daily_download_stats()
        
        # 更新统计
        self.daily_download_size_mb += file_size_mb
        self.daily_download_count += 1
        self.last_download_date = today
        self.save()


class FeedbackCategoryChoices(enum.Enum):
    DATA_ERROR = "数据错误"
    DATA_LOSS = "数据丢失"
    SYSTEM_ERROR = "系统错误"
    FEATURE_OPTIMIZATION = "功能优化"
    OTHER_SUGGESTION = "其他建议"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]


class FeedbackStatusChoices(enum.Enum):
    PENDING_CONFIRMATION = "待确认"
    CONFIRMED_PENDING_PROCESSING = "已确认待处理"
    PROCESSED = "已处理"
    UNABLE_TO_CONFIRM = "无法确认"
    INVALID_FEEDBACK = "无效反馈"

    @classmethod
    def choices(cls):
        return [(key.value, key.value) for key in cls]


class UserFeedback(models.Model):
    """用户反馈模型"""
    
    # 反馈分类（必选）
    category = models.CharField(
        max_length=100,
        choices=FeedbackCategoryChoices.choices(),
        verbose_name="反馈分类"
    )
    
    # 反馈内容
    related_link = models.URLField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="相关链接"
    )
    content = models.TextField(
        verbose_name="内容说明",
        help_text="请详细描述您的问题或建议"
    )
    
    # 联系方式（可选）
    contact_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="姓名"
    )
    contact_phone = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="电话"
    )
    contact_email = models.EmailField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="邮箱"
    )
    
    # 状态（仅管理员可见）
    status = models.CharField(
        max_length=100,
        choices=FeedbackStatusChoices.choices(),
        default=FeedbackStatusChoices.PENDING_CONFIRMATION.value,
        verbose_name="状态"
    )
    
    # 通知状态
    is_notified = models.BooleanField(
        default=False,
        verbose_name="是否已通知用户"
    )
    
    # 关联信息
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="feedback",
        verbose_name="反馈用户"
    )
    
    # 时间信息
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间"
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="更新时间"
    )
    
    class Meta:
        verbose_name = "用户反馈"
        verbose_name_plural = "用户反馈"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.category} - {self.created_at.strftime('%Y-%m-%d')}"


class StyleLink(models.Model):
    """仕样链接模型，用于生成和管理特定的搜索链接"""
    
    # 链接标识和配置
    unique_id = models.CharField(max_length=32, unique=True, verbose_name="唯一标识符", help_text="用于生成链接的唯一标识")
    search_config = models.JSONField(default=dict, verbose_name="搜索配置", help_text="JSON格式，存储搜索选项的配置")
    ai_disabled = models.BooleanField(default=True, verbose_name="AI智能搜索禁用", help_text="是否禁用AI智能搜索")
    
    # 链接管理
    name = models.CharField(max_length=255, null=True, blank=True, verbose_name="备注名称", help_text="链接的备注名称")
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="有效期", help_text="链接过期时间，为空表示永久有效")
    click_count = models.IntegerField(default=0, verbose_name="点击次数", help_text="当前点击次数")
    max_clicks = models.IntegerField(default=0, verbose_name="最大点击次数", help_text="设置为0表示无限制")
    
    # 状态
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    
    # 关联信息
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="style_links", verbose_name="创建者")
    
    # 时间信息
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        verbose_name = "仕样链接"
        verbose_name_plural = "仕样链接"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name or self.unique_id} - {self.created_by.username}"
    
    def is_expired(self):
        """检查链接是否已过期"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    def can_be_clicked(self):
        """检查链接是否可以被点击"""
        if not self.is_active:
            return False
        if self.is_expired():
            return False
        if self.max_clicks > 0 and self.click_count >= self.max_clicks:
            return False
        return True
    
    def increment_click(self):
        """增加点击次数"""
        self.click_count += 1
        self.save()
    
    def get_full_url(self, request=None):
        """获取完整的链接URL"""
        from django.urls import reverse
        if request:
            return request.build_absolute_uri(reverse('clamps:style_search', args=[self.unique_id]))
        return f"/style-search/{self.unique_id}/"


class UserStyleLinkVisit(models.Model):
    """用户访问仕样链接记录"""
    
    # 关联信息
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="style_link_visits", verbose_name="访问用户")
    style_link = models.ForeignKey(StyleLink, on_delete=models.CASCADE, related_name="visits", verbose_name="仕样链接")
    
    # 访问时间
    first_visited_at = models.DateTimeField(auto_now_add=True, verbose_name="初次访问时间")
    last_visited_at = models.DateTimeField(auto_now=True, verbose_name="上次访问时间")
    
    # 访问统计
    visit_count = models.IntegerField(default=1, verbose_name="访问次数")
    
    # 链接状态（记录访问时的状态）
    is_valid = models.BooleanField(default=True, verbose_name="链接有效状态")
    
    # 链接信息快照
    link_name = models.CharField(max_length=255, null=True, blank=True, verbose_name="链接名称")
    unique_id = models.CharField(max_length=32, verbose_name="链接唯一标识")
    
    class Meta:
        verbose_name = "用户仕样链接访问记录"
        verbose_name_plural = "用户仕样链接访问记录"
        ordering = ['-last_visited_at']
        # 确保每个用户对每个链接只有一条记录
        unique_together = [['user', 'style_link']]
    
    def __str__(self):
        return f"{self.user.username} - {self.style_link.name or self.unique_id}"

