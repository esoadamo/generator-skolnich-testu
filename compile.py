from yaml import load
from sys import argv
from pathlib import Path
from random import choice
from subprocess import check_call
from tempfile import mkdtemp
from shutil import rmtree, move


def format_question(question: dict) -> str:
    output = f"**{question['question']}**\n\n"

    if 'text' in question:
        for text in question['text']:
            output += f"{text}: " + '\\_' * (76 - len(text)) + "\n\n"
    if 'options' in question:
        output += '(' + (')' + (' ' * 10) +  '(').join(question['options']) + ')\n'

    return output


def format_category(category_name: str, category_data: dict) -> str:
    output = f"### {category_name}\n\n"
    questions = list(category_data['questions'])
    for _ in range(category_data['select']):
        question = choice(questions)
        questions.remove(question)
        output += format_question(question) + '\n'
    return output


def format_test(test_input: dict) -> str:
    test_input = dict(test_input)
    output = f"# Test: {test_input['$name']}\n\n" \
             f"**Jméno**: " + '\\_' * 40 + ' ' + \
             f"**Datum**: " + '\\_' * 20 + '\n\n'
    del test_input['$name']
    

    for category_name, category_data in test_input.items():
        output += format_category(category_name, category_data) + "\n"
    return output


def main() -> None:
    test_input_file = Path(argv[1])
    test_count = int(argv[2])
    with test_input_file.open('r') as f:
        test_input = load(f)

    dir_pdf = Path(mkdtemp(prefix="testy_pdf_", dir='/ram'))
    dir_md = Path(mkdtemp(prefix="testy_md_"))
    file_pdfs = []
    file_out = Path('/ram/testy.pdf')

    for i in range(test_count):
        print(f"{i + 1}/{test_count}")
        file_md = dir_md.joinpath(f'{i}.md')
        file_pdf = dir_pdf.joinpath(f'{i}.pdf')

        file_md.parent.mkdir(exist_ok=True, parents=True)
        file_pdf.parent.mkdir(exist_ok=True, parents=True)

        with file_md.open('w') as f:
            f.write(format_test(test_input))
        check_call([
            "pandoc",
            "--pdf-engine=xelatex",
            "-V", 'geometry:top=2cm, bottom=1.5cm, left=2cm, right=2cm',
            f"{file_md.absolute()}",
            '-o', f"{file_pdf.absolute()}"
            ])
        file_pdfs.append(file_pdf)

    check_call(["pdftk"] + [f"{x.name}" for x in file_pdfs] + ["cat", "output", "merged.pdf"], cwd=dir_pdf)
    move(dir_pdf.joinpath("merged.pdf"), file_out)
    print(file_out)
    rmtree(dir_pdf)
    rmtree(dir_md)


if __name__ == "__main__":
    main()
