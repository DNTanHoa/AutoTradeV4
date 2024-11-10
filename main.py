import sys
import logging
from strategies.simple_ma_strategy import run_simple_ma_strategy
from strategies.simple_ma_strategy_v2 import run_simple_ma_strategy_v2
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

import pyfiglet
from termcolor import colored
import colorama
import builtins

strategies = {
    1: {"name": "Simple MA Strategy", "function": run_simple_ma_strategy},
    2: {"name": "Simple MA Strategy V22", "function": run_simple_ma_strategy_v2},
}

primary_color: str = "cyan"
success_color: str = "green"
warning_color: str = "yellow"
danger_color: str = "red"

# Khởi tạo colorama để hỗ trợ màu trên Windows
colorama.init()
# Lưu trữ hàm print ban đầu
original_print = print


# Thiết lập logger để ghi log vào file
def setup_logger():
    logger = logging.getLogger("PrintLogger")
    logger.setLevel(logging.INFO)

    # Tạo handler để ghi log vào file với mã hóa UTF-8
    file_handler = TimedRotatingFileHandler("print_output.log", when="midnight", interval=1, encoding='utf-8')
    file_handler.suffix = "%Y-%m-%d"
    file_formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Thêm file handler vào logger
    logger.addHandler(file_handler)

    return logger


# Cấu hình logger
logger = setup_logger()


def custom_print(*args, sep=' ', end='\n', file=sys.stdout, flush=False):
    message = sep.join(map(str, args)) + end  # Tạo thông điệp từ các tham số

    # Ghi ra console
    original_print(message, end='', flush=flush)  # Sử dụng hàm print gốc để in ra console

    # Ghi vào file log (bỏ qua các ký tự xuống dòng thừa)
    logger.info(message.strip())  # Ghi log với thông điệp đã loại bỏ ký tự thừa


def display_header(text, color):
    # Tạo kiểu chữ với pyfiglet
    ascii_art = pyfiglet.figlet_format(text)

    # In ra màn hình với màu sắc
    colored_ascii_art = colored(ascii_art, color=color)
    print(colored_ascii_art)

    # In đường gạch dưới
    print(colored("=" * 100, color=color))


def display_info(author, version, color):
    # Hiển thị thông tin tác giả và phiên bản
    print(colored(f"Tác giả: {author}", color=color))
    print(colored(f"Phiên bản: {version}", color=color))

    # In đường gạch ngang để tách thông tin
    print(colored("-" * 100, color=color))


def display_strategy_menu():
    # Hiển thị tiêu đề chính
    display_header("AUTO-TRADE", primary_color)

    # Hiển thị thông tin tác giả và phiên bản
    display_info("Dương Nguyễn Tấn Hòa", "v1.0", primary_color)

    # Hiển thị menu chiến lược
    print(colored("Chọn chiến lược bạn muốn thực thi:", color=primary_color))
    print(colored("-" * 100, color=primary_color))

    for key, strategy in strategies.items():
        print(f"{key}. {strategy['name']}")

    # In một đường phân cách cuối cùng
    print(colored("=" * 100, primary_color))


def run_strategy(strategy_number):
    if strategy_number in strategies:
        print(f"Bạn đã chọn: {strategies[strategy_number]['name']}")
        builtins.print = custom_print
        strategies[strategy_number]['function']()
    else:
        print("Số chiến lược không hợp lệ. Vui lòng thử lại.")


if __name__ == "__main__":
    display_strategy_menu()
    try:
        user_choice = int(input("Nhập số chiến lược để thực thi: "))
        run_strategy(user_choice)
    except ValueError:
        print("Vui lòng nhập một số hợp lệ.")


# Ghi đè print bằng custom_print
builtins.print = custom_print
# Khi dùng xong, có thể tắt colorama (không bắt buộc)
colorama.deinit()
