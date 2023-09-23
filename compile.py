import asyncio
import math
from typing import Iterator
from yaml import load
from sys import argv
from pathlib import Path
from random import Random
from subprocess import check_call
from tempfile import mkdtemp, mkstemp
from shutil import rmtree, move
from os import close
from string import ascii_uppercase
from itertools import product
from multiprocessing import cpu_count


def format_question(question: dict, index: int, questions_total: int, answers: bool, rnd: Random) -> str:
    output = f"### ({index + 1}/{questions_total}) {question['question']}\n\n"

    if 'text' in question:
        for text, answer in question['text'].items():
            output += f"{text} "
            if answers:
                output += f"**_{answer}_**"
            else:
                output +='\\_' * (76 - len(text))
            output += "\n\n"
    if 'options' in question:
        options = []
        for option in question['options']:
            correct_answer = False
            if option.endswith('<'):
                correct_answer = True
                option = option[:-1]
            if answers and correct_answer:
                option = "**_{" + option + "}_**"
            else:
                option = "(" + option + ")"
            options.append(option)

        rnd.shuffle(options)
        output += (' ' * 10).join(options) + "\n\n"

    return output


def format_category(category_name: str, category_data: dict, index: int, questions_total: int, rnd: Random, answers: bool) -> str:
    output = ""
    for question in rnd.sample(category_data['questions'], k=category_data['select']):
        output += format_question(question, index, questions_total, answers, rnd) + '\n'
        index += 1
    return output


def format_test(test_input: dict, test_group: str, answers: bool) -> str:
    test_input = dict(test_input)

    group_number = int.from_bytes(test_group.encode('utf8'), 'little')

    output = f"# Test: {test_input['$name']}\n\n" \
             f"*Skupina: {test_group}*" + (", autorské řešení" if answers else "") + "\n\n" \
             f"**Jméno**: " + '\\_' * 40 + ' ' + \
             f"**Datum**: " + '\\_' * 20 + '\n\n' \
             '## Zadání\n\n'
    del test_input['$name']

    categories = test_input

    rnd = Random(group_number)
    question_index = 0
    questions_total = sum(map(lambda x: x['select'], categories.values()))

    for category_name, category_data in categories.items():
        output += format_category(category_name, category_data, question_index, questions_total, rnd, answers) + "\n"
        question_index += category_data['select']
    return output


async def create_single_test_pdf(test_input: dict, group: str, dir_pdf: Path, answers: bool) -> Path:
    handle, file_md_path = mkstemp(prefix='assigment_', suffix='.md')
    close(handle)

    file_md = Path(file_md_path)
    file_pdf = dir_pdf.joinpath(f'group_{group}.pdf')

    file_pdf.parent.mkdir(exist_ok=True, parents=True)

    with file_md.open('w') as f:
        f.write(format_test(test_input, group, answers))
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


async def create_test_pdf(test_input: dict, file_out: Path, test_count: int, answers: bool) -> Path:
    dir_pdf = Path(mkdtemp(prefix="testy_pdf_", dir='/ram'))

    pdfs_tasks = [create_single_test_pdf(test_input, group, dir_pdf, answers) for group in generate_group(test_count)]
    file_pdfs = await gather_with_concurrency(max(cpu_count() // 2, 1), *pdfs_tasks)

    check_call(["pdftk"] + [f"{x.name}" for x in file_pdfs] + ["cat", "output", "merged.pdf"], cwd=dir_pdf)
    move(dir_pdf.joinpath("merged.pdf"), file_out)
    print(file_out)
    rmtree(dir_pdf)
    return file_out


def generate_group(iterations: int = math.inf) -> Iterator[str]:
    length = 1
    while iterations > 0:
        for combo in product(ascii_uppercase, repeat=length):
            yield ''.join(combo)
            iterations -= 1
            if iterations <= 0:
                break
        length += 1


async def gather_with_concurrency(n, *coros):
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro
    return await asyncio.gather(*(sem_coro(c) for c in coros))


async def main() -> None:
    test_input_file = Path(argv[1])
    test_count = int(argv[2])

    with test_input_file.open('r') as f:
        test_input = load(f)

    file_out_assigments = Path('testy.pdf')
    file_out_solution = Path('testy_s_resenim.pdf')

    tasks = []
    for file_out, answers in ((file_out_assigments, False), (file_out_solution, True)):
        tasks.append(create_test_pdf(test_input, file_out, test_count, answers))

    await asyncio.gather(*tasks)
    check_call(['xdg-open', f"{file_out_assigments}"])


if __name__ == "__main__":
    asyncio.run(main())

