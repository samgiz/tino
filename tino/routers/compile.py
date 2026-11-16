'''REST endpoints for compiling Typst files to SVG, PDF or DOCX.'''

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from ..dependencies import get_compiler_service, require_viewer
from ..services.compiler import CompileError, CompilerService, PandocMissing

logger = logging.getLogger(__name__)

DOCX_MEDIA_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

router = APIRouter(prefix='/api/buckets/{slug}/compile', tags=['compile'])


def _parse_inputs(raw: list[str]) -> dict[str, str]:
    '''Turn repeated `input=name=value` query parameters into a dict.'''
    inputs = {}

    for item in raw:
        name, sep, value = item.partition('=')

        if not sep or not name:
            raise HTTPException(422, f'Invalid input {item!r}, expected name=value')

        inputs[name] = value

    return inputs


def _compile_failed(exc: CompileError) -> HTTPException:
    '''Build the 422 response for a failed compile.'''
    return HTTPException(422, detail={
        'message': str(exc),
        'diagnostics': exc.diagnostics,
    })


@router.get('/inputs')
async def list_inputs(
    slug: str,
    user=Depends(require_viewer),  # pylint: disable=unused-argument
    svc: CompilerService = Depends(get_compiler_service),
):
    '''Return the inputs the bucket declares in its tino.toml, name to allowed values.'''
    return {'inputs': svc.list_inputs(slug)}


@router.get('/pdf/{path:path}')
async def compile_pdf(
    slug: str, path: str,
    input: list[str] = Query(default=[]),  # pylint: disable=redefined-builtin
    user=Depends(require_viewer),
    svc: CompilerService = Depends(get_compiler_service),
):
    '''Compile a .typ file and return the PDF.'''
    logger.info('Compiling PDF for %s/%s (user: %s)', slug, path, user.username)
    try:
        pdf_path = svc.compile_pdf(slug, path, _parse_inputs(input))
        filename = path.rsplit('/', maxsplit=1)[-1].replace('.typ', '.pdf')

        return FileResponse(
            pdf_path,
            filename=filename,
            media_type='application/pdf',
            background=BackgroundTask(pdf_path.unlink, missing_ok=True),
        )

    except FileNotFoundError as exc:
        raise HTTPException(404, 'File not found') from exc

    except CompileError as exc:
        raise _compile_failed(exc) from exc

    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/docx/{path:path}')
async def compile_docx(
    slug: str, path: str,
    input: list[str] = Query(default=[]),  # pylint: disable=redefined-builtin
    user=Depends(require_viewer),
    svc: CompilerService = Depends(get_compiler_service),
):
    '''Compile a .typ file and return a DOCX (via Typst's HTML export and pandoc).'''
    logger.info('Compiling DOCX for %s/%s (user: %s)', slug, path, user.username)
    try:
        docx_path = svc.compile_docx(slug, path, _parse_inputs(input))
        filename = path.rsplit('/', maxsplit=1)[-1].replace('.typ', '.docx')

        return FileResponse(
            docx_path,
            filename=filename,
            media_type=DOCX_MEDIA_TYPE,
            background=BackgroundTask(docx_path.unlink, missing_ok=True),
        )

    except FileNotFoundError as exc:
        raise HTTPException(404, 'File not found') from exc

    except PandocMissing as exc:
        raise HTTPException(501, str(exc)) from exc

    except CompileError as exc:
        raise _compile_failed(exc) from exc

    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get('/svg/{path:path}')
async def compile_svg(
    slug: str, path: str,
    input: list[str] = Query(default=[]),  # pylint: disable=redefined-builtin
    user=Depends(require_viewer),
    svc: CompilerService = Depends(get_compiler_service),
):
    '''Compile a .typ file and return a list of SVG strings (one per page).'''
    logger.debug('Compiling SVG for %s/%s (user: %s)', slug, path, user.username)
    try:
        pages = svc.compile_svg(slug, path, _parse_inputs(input))
        return {'pages': pages}

    except FileNotFoundError as exc:
        raise HTTPException(404, 'File not found') from exc

    except CompileError as exc:
        raise _compile_failed(exc) from exc

    except RuntimeError as exc:
        raise HTTPException(422, str(exc)) from exc
