from django.core.management.base import BaseCommand
import pandas as pd

from core.models import Grade, Subject, Topic, LearningObjective


class Command(BaseCommand):
    help = "Import Learning Objectives from an Excel file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file_path",
            type=str,
            help="Path to the Excel file containing LOs"
        )

    def handle(self, *args, **options):
        file_path = options["file_path"]

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(str(e)))
            return

        required_columns = [
            "Grade",
            "Subject",
            "Topic",
            "LO Code",
            "LO Description",
        ]

        for col in required_columns:
            if col not in df.columns:
                self.stderr.write(
                    self.style.ERROR(f"Missing required column: {col}")
                )
                return

        created = 0
        skipped = 0

        for idx, row in df.iterrows():
            grade_name = str(row["Grade"]).strip()
            subject_name = str(row["Subject"]).strip()
            topic_name = str(row["Topic"]).strip()
            lo_code = str(row["LO Code"]).strip()
            lo_desc = str(row["LO Description"]).strip()

            # Skip empty rows safely
            if not all([grade_name, subject_name, topic_name, lo_code]):
                skipped += 1
                continue

            grade, _ = Grade.objects.get_or_create(
                name=grade_name
            )

            subject, _ = Subject.objects.get_or_create(
                name=subject_name
            )

            topic, _ = Topic.objects.get_or_create(
                name=topic_name,
                grade=grade,
                subject=subject
            )

            lo, was_created = LearningObjective.objects.get_or_create(
                grade=grade,
                subject=subject,
                topic=topic,
                code=lo_code,
                defaults={
                    "description": lo_desc
                }
            )

            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"LO import complete → Created: {created}, Skipped: {skipped}"
            )
        )
