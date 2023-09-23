import asyncio
from yaml import load
from sys import argv
from pathlib import Path
from random import Random
from subprocess import check_call
from tempfile import mkdtemp, mkstemp
from shutil import rmtree, move
from os import close


def format_question(question: dict, index: int, questions_total: int) -> str:
    output = f"### ({index + 1}/{questions_total}) {question['question']}\n\n"

    if 'text' in question:
        for text in question['text']:
            output += f"{text}: " + '\\_' * (76 - len(text)) + "\n\n"
    if 'options' in question:
        output += '(' + (')' + (' ' * 10) +  '(').join(question['options']) + ')\n'

    return output


def format_category(category_name: str, category_data: dict, index: int, questions_total: int, rnd: Random) -> str:
    output = ""
    for question in rnd.sample(category_data['questions'], k=category_data['select']):
        output += format_question(question, index, questions_total) + '\n'
        index += 1
    return output


def format_test(test_input: dict, version: int) -> str:
    test_input = dict(test_input)

    version_str = hex(10 + version).upper()[2:]

    output = f"# Test: {test_input['$name']}\n\n" \
             f"*Skupina: {version_str}*\n\n" \
             f"**Jméno**: " + '\\_' * 40 + ' ' + \
             f"**Datum**: " + '\\_' * 20 + '\n\n' \
             '## Zadání\n\n'
    del test_input['$name']

    categories = test_input

    rnd = Random(version)
    question_index = 0
    questions_total = sum(map(lambda x: x['select'], categories.values()))

    for category_name, category_data in categories.items():
        output += format_category(category_name, category_data, question_index, questions_total, rnd) + "\n"
        question_index += category_data['select']
    return output


async def create_test_pdf(test_input: dict, index: int, dir_pdf: Path) -> Path:
    handle, file_md_path = mkstemp(prefix='assigment_', suffix='.md')
    close(handle)

    file_md = Path(file_md_path)
    file_pdf = dir_pdf.joinpath('%03d.pdf' % index)

    file_pdf.parent.mkdir(exist_ok=True, parents=True)

    with file_md.open('w') as f:
        f.write(format_test(test_input, index))
    process = await asyncio.subprocess.create_subprocess_exec(
        "pandoc",
        "--pdf-engine=xelatex",
        "-V", 'geometry:top=2cm, bottom=1.5cm, left=2cm, right=2cm',
        f"{file_md.absolute()}",
        '-o', f"{file_pdf.absolute()}"
        )
    await process.communicate()
    assert process.returncode == 0
    file_md.unlink()
    print(f'[*] {file_pdf}')
    return file_pdf


async def main() -> None:
    test_input_file = Path(argv[1])
    test_count = int(argv[2])

    dir_pdf = Path(mkdtemp(prefix="testy_pdf_", dir='/ram'))
    file_out = Path('/ram/testy.pdf')

    with test_input_file.open('r') as f:
        test_input = load(f)

    pdfs_tasks = [asyncio.create_task(create_test_pdf(test_input, i, dir_pdf)) for i in range(test_count)]
    file_pdfs = await asyncio.gather(*pdfs_tasks)

    check_call(["pdftk"] + [f"{x.name}" for x in file_pdfs] + ["cat", "output", "merged.pdf"], cwd=dir_pdf)
    move(dir_pdf.joinpath("merged.pdf"), file_out)
    print(file_out)
    rmtree(dir_pdf)
    check_call(['xdg-open', f"{file_out}"])


if __name__ == "__main__":
    asyncio.run(main())

