'''
import subprocess         #запуск внешних прог
import logging            #логирование событий
from pathlib import Path  #работа с путями
import argparse           #парсинг и разбор аргументов кс
import requests           #скачивание файлов и получение данных HTTP
import zipfile            #архивация и разархивация



class ScanRunner:
    def __init__(self, tool_url, report_dir, report_name, target_dir):
        self.tool_url = tool_url
        self.report_dir = Path(report_dir)
        self.report_name = report_name
        self.target_dir = target_dir

        self.tool_path = self.report_dir / 'tool.zip'
        self.extract_path = self.report_dir / 'tool'

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)




    def check_connection_host(self):   #доступ к сайту
        try:
            response = requests.get(self.tool_url)
            if response.status_code == 200:
                self.logger.info(f"Connected to {self.tool_url}")
                return True
            else:
                self.logger.error(f"Connection to {self.tool_url} failed")
                return False
        except Exception as e:
            self.logger.error(f"Connection to {self.tool_url} failed: {e}")
            return False






    def tool_download(self):    #скачивание kingfisher
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Downloading {self.tool_url}")    #скачивание инструмента
        response = requests.get(self.tool_url)

        with open(self.tool_path, 'wb') as f:
            f.write(response.content)

        self.logger.info(f"Downloaded in {self.tool_path}")

        if zipfile.is_zipfile(self.tool_path):
            self.logger.info(f"Unzipping {self.tool_path}")
            with zipfile.ZipFile(self.tool_path, 'r') as zip_ref:
                zip_ref.extractall(self.extract_path)

            self.logger.info(f"Extracted in {self.extract_path}")






    def scan(self):     #сканирорвание
        self.logger.info('Starting scan')

        report_file = Path(self.report_dir) / self.report_name
        exe_path = self.extract_path / "kingfisher.exe"

        # команда для сканирования
        command = [
            str(self.exe_path),    # сам исполняемый файл
            "scan",
            self.target_dir,           # что сканировать
            "--format", "json"         # формат отчета
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        # сохраняем "отчет"
        with open(report_file, "w") as f:
            f.write(result.stdout)

        self.logger.info(f"Scanned saved to {report_file }")





    def report_parser(self):
        report_file = self.report_dir / self.report_name

        if not report_file.exists():
            self.logger.error("Отчет не найден")
            return

        with open(report_file, "r") as f:
            content = f.readlines()

        # Пример: считаем строки с "VULN"
        vuln_count = sum(1 for line in content if "VULN" in line)

        self.logger.info(f"Найдено уязвимостей: {vuln_count}")





    def run(self):
        if not self.check_connection_host():
            return

        self.tool_download()
        self.scan()
        self.report_parser()




if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--report_dir", default="reports")
    parser.add_argument("--report_name", default="report.txt")

    args = parser.parse_args()

    runner = ScanRunner(
        tool_url=args.url,
        report_dir=args.report_dir,
        report_name=args.report_name,
        target_dir=args.target
    )

    runner.run()
'''


import subprocess         # запуск внешних программ
import logging            # логирование событий
from pathlib import Path  # работа с путями
import argparse           # парсинг аргументов
import requests           # скачивание файлов
import zipfile            # работа с архивами
import json


class ScanRunner:
    def __init__(self, tool_url, report_dir, report_name, target_dir):
        self.tool_url = tool_url
        self.report_dir = Path(report_dir)
        self.report_name = report_name
        self.target_dir = target_dir

        self.tool_path = self.report_dir / 'tool.zip'
        self.extract_path = self.report_dir / 'tool'
        self.exe_path = None  # <<< ИСПРАВЛЕНО: путь к exe задаем после распаковки

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def check_connection_host(self):
        try:
            response = requests.get(self.tool_url)
            if response.status_code == 200:
                self.logger.info(f"Connected to {self.tool_url}")
                return True
            else:
                self.logger.error(f"Connection to {self.tool_url} failed")
                return False
        except Exception as e:
            self.logger.error(f"Connection to {self.tool_url} failed: {e}")
            return False

    def tool_download(self):
        self.report_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Downloading {self.tool_url}")
        response = requests.get(self.tool_url)


        with open(self.tool_path, 'wb') as f:
            f.write(response.content)

        self.logger.info(f"Downloaded in {self.tool_path}")

        if zipfile.is_zipfile(self.tool_path):
            self.logger.info(f"Unzipping {self.tool_path}")
            with zipfile.ZipFile(self.tool_path, 'r') as zip_ref:
                zip_ref.extractall(self.extract_path)
            self.logger.info(f"Extracted in {self.extract_path}")

        # <<< ИСПРАВЛЕНО: после распаковки задаем путь к exe
        self.exe_path = self.extract_path / "kingfisher.exe"
        if not self.exe_path.exists():
            self.logger.error(f"Executable not found: {self.exe_path}")
            raise FileNotFoundError(f"{self.exe_path} not found")

    def scan(self):
        self.logger.info('Starting scan')

        report_file = Path(self.report_dir) / self.report_name


        command = [
            str(self.exe_path),
            "scan",
            self.target_dir,
            "--format", "json"
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            self.logger.error(f"Scan failed: {result.stderr}")
            return

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(result.stdout)

        self.logger.info(f"Scan saved to {report_file}")

    def bandit_scan(self):
        self.logger.info('Starting Bandit scan')

        bandit_report = self.report_dir / "bandit_report.json"

        command = [
            "bandit",
            "-r", str(self.target_dir),
            "-f", "json",
            "-o", str(bandit_report)
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            self.logger.error(f"Bandit scan failed: {result.stderr}")
            return

        if bandit_report.exists():
            with open(bandit_report, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    vuln_count = len(data.get("results", []))
                    self.logger.info(f"Bandit found vulnerabilities: {vuln_count}")
                except json.JSONDecodeError:
                    self.logger.error("Failed to parse Bandit report")
        else:
            self.logger.error("Bandit report file not found")

    def report_parser(self):
        report_file = self.report_dir / self.report_name

        if not report_file.exists():
            self.logger.error("Report file not found")
            return

        with open(report_file, "r", encoding="utf-8") as f:
            content = f.readlines()

        vuln_count = sum(1 for line in content if "VULN" in line)
        self.logger.info(f"Found vulnerabilities: {vuln_count}")

    def run(self):
        if not self.check_connection_host():
            return
        self.tool_download()
        self.scan()
        self.report_parser()
        self.bandit_scan()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Direct link to kingfisher zip")
    parser.add_argument("--target", required=True, help="Folder to scan")
    parser.add_argument("--report_dir", default="reports", help="Directory for report")
    parser.add_argument("--report_name", default="report.txt", help="Report file name")
    args = parser.parse_args()

    runner = ScanRunner(
        tool_url=args.url,
        report_dir=args.report_dir,
        report_name=args.report_name,
        target_dir=args.target
    )

    runner.run()
