from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from clamps.models import Category, Product


class Command(BaseCommand):
    help = '初始化数据库数据，包括分类和示例产品'

    def handle(self, *args, **options):
        self.stdout.write('开始初始化数据...')
        
        # 创建分类
        categories_data = [
            'X2C-C', 'X2C-X', 'X2C-V2-C', 'X2C-V2-X', 'X2C-V3-C', 'X2C-V3-X'
        ]
        
        for category_name in categories_data:
            category, created = Category.objects.get_or_create(name=category_name)
            if created:
                self.stdout.write(f'创建分类: {category_name}')
            else:
                self.stdout.write(f'分类已存在: {category_name}')
        
        # 创建示例产品数据
        sample_products = [
            {
                'category': 'X2C-C',
                'description': 'C型标准焊钳',
                'drawing_no_1': 'X2C-C-001',
                'sub_category_type': '中型',
                'stroke': 25.0,
                'clamping_force': 4000.0,
                'weight': 15.5,
                'throat_depth': 100.0,
                'throat_width': 50.0,
                'transformer': 'RT552',
                'electrode_arm_end': '握杆（铝）',
                'motor_manufacturer': 'FANUC',
                'has_balance': '有',
            },
            {
                'category': 'X2C-X',
                'description': 'X型偏心焊钳',
                'drawing_no_1': 'X2C-X-001',
                'sub_category_type': '大型',
                'stroke': 30.0,
                'clamping_force': 6000.0,
                'weight': 22.3,
                'throat_depth': 150.0,
                'throat_width': 75.0,
                'transformer': 'RT752',
                'electrode_arm_end': 'TIP BASE（F 型）',
                'motor_manufacturer': 'KUKA',
                'has_balance': '有',
                'static_arm_eccentricity': 25.0,
                'moving_arm_eccentricity': 30.0,
            },
            {
                'category': 'X2C-V2-C',
                'description': 'V2型C型焊钳',
                'drawing_no_1': 'X2C-V2-C-001',
                'sub_category_type': '小型',
                'stroke': 20.0,
                'clamping_force': 3000.0,
                'weight': 12.8,
                'throat_depth': 80.0,
                'throat_width': 40.0,
                'transformer': 'RT452',
                'electrode_arm_end': '握杆（SBA）',
                'motor_manufacturer': 'YASKAWA',
                'has_balance': '无',
            },
            {
                'category': 'X2C-V2-X',
                'description': 'V2型X型焊钳',
                'drawing_no_1': 'X2C-V2-X-001',
                'sub_category_type': '中型',
                'stroke': 28.0,
                'clamping_force': 5000.0,
                'weight': 18.7,
                'throat_depth': 120.0,
                'throat_width': 60.0,
                'transformer': 'RT706',
                'electrode_arm_end': 'GUN HEAD（?40）',
                'motor_manufacturer': 'ABB',
                'has_balance': '有',
                'static_arm_eccentricity': 20.0,
                'moving_arm_eccentricity': 25.0,
            },
            {
                'category': 'X2C-V3-C',
                'description': 'V3型C型焊钳',
                'drawing_no_1': 'X2C-V3-C-001',
                'sub_category_type': '特殊',
                'stroke': 35.0,
                'clamping_force': 7000.0,
                'weight': 28.5,
                'throat_depth': 180.0,
                'throat_width': 90.0,
                'transformer': 'RT906',
                'electrode_arm_end': 'GUN HEAD（?50）',
                'motor_manufacturer': 'FANUC',
                'has_balance': '有',
            },
            {
                'category': 'X2C-V3-X',
                'description': 'V3型X型焊钳',
                'drawing_no_1': 'X2C-V3-X-001',
                'sub_category_type': '仙鹤型',
                'stroke': 40.0,
                'clamping_force': 8000.0,
                'weight': 32.1,
                'throat_depth': 200.0,
                'throat_width': 100.0,
                'transformer': 'ITS85',
                'electrode_arm_end': 'GUN HEAD（?60）',
                'motor_manufacturer': 'KUKA',
                'has_balance': '有',
                'static_arm_eccentricity': 35.0,
                'moving_arm_eccentricity': 40.0,
            },
        ]
        
        for product_data in sample_products:
            category_name = product_data.pop('category')
            category = Category.objects.get(name=category_name)
            product_data['category'] = category
            
            product, created = Product.objects.get_or_create(
                drawing_no_1=product_data['drawing_no_1'],
                defaults=product_data
            )
            
            if created:
                self.stdout.write(f'创建产品: {product_data["drawing_no_1"]}')
            else:
                self.stdout.write(f'产品已存在: {product_data["drawing_no_1"]}')
        
        self.stdout.write(self.style.SUCCESS('数据初始化完成！'))
        self.stdout.write(f'分类总数: {Category.objects.count()}')
        self.stdout.write(f'产品总数: {Product.objects.count()}')

