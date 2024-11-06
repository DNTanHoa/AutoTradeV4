import logging
from logging.handlers import TimedRotatingFileHandler
import builtins


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


# Hàm ghi đè print
def custom_print(*args, sep=' ', end='\n', flush=False):
    # Cấu hình logger
    logger = setup_logger()

    message = sep.join(map(str, args)) + end  # Tạo thông điệp từ các tham số

    # Ghi ra console
    builtins.print(message, end='', flush=flush)  # Sử dụng builtins.print để in ra console

    # Ghi vào file log (bỏ qua các ký tự xuống dòng thừa)
    logger.info(message.strip())  # Ghi log với thông điệp đã loại bỏ ký tự thừa
