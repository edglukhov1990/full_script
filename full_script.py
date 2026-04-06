






import subprocess  # запуск внешних программ
import logging  # логирование событий
from pathlib import Path  # работа с путями
import argparse  # парсинг аргументов
import requests  # скачивание файлов
import zipfile  # работа с архивами
import json


class ScanRunner:
    def __init__(self, tool_url, report_dir, report_name, target_dir, run_bandit=False):
        self.tool_url = tool_url
        self.report_dir = Path(report_dir)
        self.report_name = report_name
        self.target_dir = target_dir
        self.run_bandit = run_bandit

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

        # Если уже скачан — не качаем снова
        if not self.tool_path.exists():
            self.logger.info(f"Downloading {self.tool_url}")
            response = requests.get(self.tool_url, timeout=60)

            with open(self.tool_path, 'wb') as f:
                f.write(response.content)
            self.logger.info(f"Downloaded in {self.tool_path}")
        else:
            self.logger.info("Tool already downloaded, skipping")

        if not self.extract_path.exists():
            if zipfile.is_zipfile(self.tool_path):
                self.logger.info(f"Unzipping {self.tool_path}")
                with zipfile.ZipFile(self.tool_path, 'r') as zip_ref:
                    zip_ref.extractall(self.extract_path)
                self.logger.info(f"Extracted in {self.extract_path}")

        self.exe_path = self.extract_path / "kingfisher.exe"
        if not self.exe_path.exists():
            self.logger.error(f"Executable not found: {self.exe_path}")
            raise FileNotFoundError(f"{self.exe_path} not found")

    def scan(self):
        self.logger.info('Starting scan')

        report_file = self.report_dir / self.report_name

        command = [
            str(self.exe_path),
            "scan",
            str(self.target_dir),
            "--output",
            str(report_file),
            "--format",
            "json"
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        # ИСПРАВЛЕНО: Kingfisher пишет инфо-сообщения в stderr с ненулевым кодом —
        # это не ошибка. Проверяем факт создания файла отчёта, а не returncode.
        if result.stderr:
            self.logger.info(f"Kingfisher info: {result.stderr.strip()}")

        if report_file.exists():
            self.logger.info(f"Scan saved to {report_file}")
        else:
            self.logger.error("Report file was not created")
            return

    def report_parser(self):
        report_file = self.report_dir / self.report_name

        if not report_file.exists():
            self.logger.error("Report file not found")
            return

        try:
            with open(report_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            runs = data.get("runs", [])

            if not runs:
                self.logger.info("No scan results found")
                return

            results = runs[0].get("results", [])

            vuln_count = len(results)

            self.logger.info(f"Found vulnerabilities: {vuln_count}")

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON report")

    def bandit_scan(self):
        self.logger.info("Starting Bandit scan")



        bandit_report = self.report_dir / "bandit_report.json"

        command = [
            "bandit",
            "-r",
            str(self.target_dir),
            "-f",
            "json",
            "-o",
            str(bandit_report),
            "--exclude",
            ".venv",
        ]

        result = subprocess.run(command, capture_output=True, text=True)

        # Bandit возвращает 0 = нет уязвимостей, 1 = найдены уязвимости, 2 = ошибка
        if result.returncode == 2:
            self.logger.error(f"Bandit scan failed: {result.stderr}")
            return

        if result.returncode in (0, 1):
            self.logger.info("Bandit scan completed")

        if bandit_report.exists():
            try:
                with open(bandit_report, "r", encoding="utf-8") as f:
                    data = json.load(f)

                vuln_count = len(data.get("results", []))
                self.logger.info(f"Bandit found vulnerabilities: {vuln_count}")

            except json.JSONDecodeError:
                self.logger.error("Failed to parse Bandit report")

        else:
            self.logger.error("Bandit report file not found")

    def run(self):
        if not self.check_connection_host():
            return
        self.tool_download()
        self.scan()
        self.report_parser()

        if self.run_bandit:
            self.bandit_scan()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url",
                        default="https://github.com/mongodb/kingfisher/releases/download/v1.94.0/kingfisher-windows-x64.zip",
                        help="Direct link to kingfisher zip")
    parser.add_argument("--target", default=".", help="Folder to scan(default current dir)")
    parser.add_argument("--report_dir", default="reports", help="Directory for report")
    parser.add_argument("--report_name", default="report.json", help="Report file name")
    parser.add_argument("--bandit", action="store_true", help="Run Bandit scan")
    args = parser.parse_args()

    runner = ScanRunner(
        tool_url=args.url,
        report_dir=args.report_dir,
        report_name=args.report_name,
        target_dir=args.target,
        run_bandit=args.bandit,
    )

    runner.run()