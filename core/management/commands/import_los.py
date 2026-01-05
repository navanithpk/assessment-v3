from django.core.management.base import BaseCommand
from core.models import Grade, Subject, Topic, LearningObjective
import pandas as pd


class Command(BaseCommand):
    help = "Import Learning Objectives from an Excel file"

    def add_arguments(self, parser):
        parser.add_argument(
            "file",
            type=str,
            help="Path to Excel file (e.g. learning_objectives.xlsx)"
        )

    def handle(self, *args, **options):
        file_path = options["file"]

        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to read Excel file: {e}"))
            return

        required_cols = {
            "grade",
            "subject",
            "topic",
            "lo_code",
            "lo_description",
        }

        if not required_cols.issubset(df.columns):
            self.stderr.write(
                self.style.ERROR(
                    f"Excel must contain columns: {', '.join(required_cols)}"
                )
            )
            return

        created_lo = 0
        skipped_lo = 0

        for idx, row in df.iterrows():
            grade_name = str(row["grade"]).strip()
            subject_name = str(row["subject"]).strip()
            topic_name = str(row["topic"]).strip()
            lo_code = str(row["lo_code"]).strip()
            lo_desc = str(row["lo_description"]).strip()

            if not all([grade_name, subject_name, topic_name, lo_code, lo_desc]):
                self.stdout.write(
                    self.style.WARNING(f"Row {idx + 2}: Missing required field, skipped")
                )
                skipped_lo += 1
                continue

            grade, _ = Grade.objects.get_or_create(name=grade_name)
            subject, _ = Subject.objects.get_or_create(name=subject_name)
            topic, _ = Topic.objects.get_or_create(
                name=topic_name,
                grade=grade,
                subject=subject,
            )

            lo, created = LearningObjective.objects.get_or_create(
                topic=topic,
                code=lo_code,
                defaults={
                    "description": lo_desc,
                    "grade": grade,
                    "subject": subject,
                },
            )

            if created:
                created_lo += 1
            else:
                skipped_lo += 1

        self.stdout.write(self.style.SUCCESS("Import completed"))
        self.stdout.write(self.style.SUCCESS(f"Created LOs: {created_lo}"))
        self.stdout.write(self.style.WARNING(f"Skipped (duplicates/invalid): {skipped_lo}"))
