import asyncio
import math
from typing import Iterator, Optional, Set, Tuple
from yaml import load, Loader
from sys import argv
from pathlib import Path
from random import Random
from subprocess import check_call
from tempfile import mkdtemp, mkstemp
from shutil import rmtree, move
from os import close
from string import ascii_uppercase
from itertools import product
from datetime import datetime, timedelta

from models import Question, Category, Test


def format_question(question: Question, index: int, questions_total: int, answers: bool, rnd: Random) -> str:
    """
    Format single question from the test
    :param question: question data
    :param index: current question index
    :param questions_total: total number of questions
    :param answers: True if answers should be included
    :param rnd: random generator for given group
    :return: formatted question text
    """
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


def format_category(category_name: str, category_data: Category, index: int, questions_total: int, rnd: Random, answers: bool, last_questions: Optional[Set[int]] = None) -> Tuple[str, Set[int]]:
    """
    Formats single category of questions
    :param category_name: category name
    :param category_data: category data
    :param index: current question index
    :param questions_total: total number of questions
    :param rnd: random generator for given group
    :param answers: True if answers should be included
    :param last_questions: IDs of questions used in last test
    :return: formatted category text and IDs of used questions
    """
    output = ""
    question_ids = set()

    questions_all = category_data['questions']
    select_count = category_data['select']

    questions_unused = [question for question in questions_all if question["_id"] not in last_questions]
    questions_used = [question for question in questions_all if question["_id"] in last_questions]
    questions_missing_count = select_count - len(questions_unused)
    if questions_missing_count > 0:
        questions_unused += rnd.sample(questions_used, k=questions_missing_count)

    for question in rnd.sample(questions_unused, k=select_count):
        output += format_question(question, index, questions_total, answers, rnd) + '\n'
        question_ids.add(question["_id"])
        index += 1
    return output, question_ids


def load_test_categories(test_input: Test) -> dict:
    """
    Load test categories from the input file, including all includes
    Adds IDs to questions
    :param test_input: loaded file
    :return: all test categories
    """
    categories = {}

    if 'includes' in test_input:
        for include in test_input['includes']:
            with open(include + '.yaml', 'r') as f:
                categories.update(load_test_categories(load(f, Loader)))

    categories.update(test_input.get('categories', {}))

    question_id = 0
    for category in categories.values():
        for question in category['questions']:
            question["_id"] = question_id
            question_id += 1

    return categories


def group_to_random(group: str) -> Random:
    """
    Create a random generator from the group name
    :param group: test group name
    :return: Random object instance
    """
    group_number = int.from_bytes(group.encode('utf8'), 'little')
    return Random(group_number)


def format_test(test_input: Test, test_group: str, answers: bool, last_questions: Optional[Set[int]] = None) -> Tuple[str, Set[int]]:
    """
    Format a single test

    :param test_input: test input data with categories
    :param test_group: test group to generate for
    :param answers: True if answers should be included
    :param last_questions: set of IDs of questions used in previous tests
    :return: test text content and IDs of used questions
    """

    output = f"# Test: {test_input['name']}\n\n" \
             f"*Skupina: {test_group}*" + (", autorské řešení" if answers else "") + "\n\n" \
             f"**Jméno**: " + '\\_' * 30 + ' ' + \
             f"**Datum**: " + '\\_' * 20 + '\n\n' \
             '## Zadání\n\n'

    categories = test_input['categories']

    last_questions = last_questions or set()
    rnd = group_to_random(test_group)
    question_index = 0
    questions_total = sum(map(lambda x: x['select'], categories.values()))

    question_ids = set()
    for category_name, category_data in categories.items():
        content, questions = format_category(category_name, category_data, question_index, questions_total, rnd, answers, last_questions)
        question_ids.update(questions)
        output += content + "\n"
        question_index += category_data['select']
    return output, question_ids


async def create_single_test_pdf(test_content: str, group: str, dir_pdf: Path) -> Path:
    """
    Create a PDF file with rendered test for a single group
    :param test_content: raw text content of the test
    :param group: group name
    :param dir_pdf: where to save the output file
    :return: path to the created file
    """
    handle, file_md_path = mkstemp(prefix='assigment_', suffix='.md')
    close(handle)

    file_md = Path(file_md_path)
    file_pdf = dir_pdf.joinpath('group_' + group.replace(' / ', '_') + '.pdf')

    file_pdf.parent.mkdir(exist_ok=True, parents=True)

    with file_md.open('w') as f:
        f.write(test_content)
    process = await asyncio.subprocess.create_subprocess_exec(
        "pandoc",
        "--pdf-engine=xelatex",
        "-V", 'geometry:top=1cm, bottom=1cm, left=1cm, right=1cm',
        "-V", "fontsize=12pt",
        f"{file_md.absolute()}",
        '-o', f"{file_pdf.absolute()}"
        )
    await process.communicate()
    assert process.returncode == 0
    file_md.unlink()
    print(f'[*] {file_pdf}')
    return file_pdf


async def create_test_pdf(test_input: Test, file_out: Path, test_count: int, answers: bool) -> Path:
    """
    Create a PDF file with rendered test for the selected number of groups
    :param test_input: test input data
    :param file_out: where to save the output file
    :param test_count: how many groups to generate
    :param answers: True if answers should be included
    :return: path to the created file
    """
    dir_pdf = Path(mkdtemp(prefix="testy_pdf_", dir='/tmp'))

    last_questions = set()
    formatted_tests = []
    for group in generate_group(test_count):
        formated_test, questions = format_test(test_input, group, answers, last_questions)
        last_questions = questions
        formatted_tests.append((formated_test, group))

    pdfs_tasks = [create_single_test_pdf(content, group, dir_pdf) for i, (content, group) in enumerate(formatted_tests)]
    file_pdfs = await gather_with_concurrency(8, *pdfs_tasks)

    check_call(["pdftk"] + [f"{x.name}" for x in file_pdfs] + ["cat", "output", "merged.pdf"], cwd=dir_pdf)
    move(dir_pdf.joinpath("merged.pdf"), file_out)
    print(file_out)
    rmtree(dir_pdf)
    return file_out


def generate_group(iterations: int = math.inf) -> Iterator[str]:
    """
    Generate group names
    :param iterations: how many groups to generate
    :return: group names
    """
    length = 1

    # offset to match the school year
    year_start = datetime.now() - timedelta(days=7*30)
    year_end = year_start + timedelta(days=365)

    while iterations > 0:
        for combo in product(ascii_uppercase, repeat=length):
            yield ''.join(combo) + f" ({year_start.year} / {year_end.year})"
            iterations -= 1
            if iterations <= 0:
                break
        length += 1


async def gather_with_concurrency(n, *coros):
    """
    Run coroutines with a limit on concurrency
    :param n: how many coroutines can run at the same time
    :param coros: coroutines to run
    :return: results of coroutines
    """
    semaphore = asyncio.Semaphore(n)

    async def sem_coro(coro):
        async with semaphore:
            return await coro
    return await asyncio.gather(*(sem_coro(c) for c in coros))


async def main() -> None:
    test_input_file = Path(argv[1])
    test_count = int(argv[2])

    with test_input_file.open('r') as f:
        test_input = load(f, Loader)
    test_input['categories'] = load_test_categories(test_input)

    file_out_assigments = Path('testy.pdf')
    file_out_solution = Path('testy_s_resenim.pdf')

    tasks = []
    for file_out, answers in ((file_out_assigments, False), (file_out_solution, True)):
        tasks.append(create_test_pdf(test_input, file_out, test_count, answers))

    await asyncio.gather(*tasks)
    check_call(['xdg-open', f"{file_out_assigments}"])


if __name__ == "__main__":
    asyncio.run(main())

