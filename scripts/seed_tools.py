import sys
import os
import mongoengine

# Add parent directory to path so we can import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from app.config import Config
from app.models.tool import Tool

def seed_tools():
    # Connect to DB
    mongoengine.connect(host=Config.MONGODB_SETTINGS['host'])

    # Check if tools already exist
    if Tool.objects.count() > 0:
        print("Tools already seeded. Deleting existing tools to re-seed...")
        Tool.objects.delete()

    print("Seeding tools...")
    tools_data = [
        {
            'name': 'Form Automation',
            'description': 'Tự động hóa hoàn toàn quy trình điền và gửi Google Form với trí tuệ nhân tạo và hệ thống định tuyến thông minh.',
            'category': 'Tự động hóa',
            'status': 'active',
            'route': '/tool/form-automation',
            'icon': 'FiFileText'
        },
        {
            'name': 'Intelligent OCR',
            'description': 'Trích xuất dữ liệu tự động từ hình ảnh, hóa đơn và tài liệu giấy tờ bằng công nghệ OCR tiên tiến.',
            'category': 'Dữ liệu',
            'status': 'upcoming',
            'route': '#',
            'icon': 'FiFile'
        },
        {
            'name': 'Data Extractor',
            'description': 'Tự động quét và thu thập dữ liệu có cấu trúc từ bất kỳ trang web nào chỉ với một đường link.',
            'category': 'Dữ liệu',
            'status': 'upcoming',
            'route': '#',
            'icon': 'FiDatabase'
        },
        {
            'name': 'Social Media Bot',
            'description': 'Lập lịch và tự động đăng bài viết, tương tác với khách hàng trên đa nền tảng mạng xã hội.',
            'category': 'Tự động hóa',
            'status': 'upcoming',
            'route': '#',
            'icon': 'FiMessageSquare'
        },
        {
            'name': 'Voice to Text AI',
            'description': 'Chuyển đổi âm thanh cuộc họp, phỏng vấn thành văn bản có độ chính xác cao bằng mô hình Whisper.',
            'category': 'AI & Machine Learning',
            'status': 'upcoming',
            'route': '#',
            'icon': 'FiMic'
        },
        {
            'name': 'SEO Keyword Analyzer',
            'description': 'Phân tích mật độ từ khóa, tối ưu hóa on-page SEO và theo dõi thứ hạng trên công cụ tìm kiếm.',
            'category': 'Marketing',
            'status': 'upcoming',
            'route': '#',
            'icon': 'FiTrendingUp'
        }
    ]

    for data in tools_data:
        tool = Tool(**data)
        tool.save()

    print("Tools seeded successfully!")

if __name__ == '__main__':
    seed_tools()
