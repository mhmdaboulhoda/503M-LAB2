# validators.py
#
# validators for file uploads, etc.

from django.utils.translation import gettext as _

from helpdesk import settings as helpdesk_settings

# TODO: can we use the builtin Django validator instead?
# see:
# https://docs.djangoproject.com/en/4.0/ref/validators/#fileextensionvalidator


def validate_file_extension(value):
    import os

    from django.core.exceptions import ValidationError

    if not helpdesk_settings.HELPDESK_VALIDATE_ATTACHMENT_TYPES:
        return

    # Part C Layer-2 fix: validate on the base name only (never a directory
    # component the sender may have smuggled in via the filename).
    name = os.path.basename(value.name)

    # Part C Layer-2 fix: reject any filename with more than one dot OUTRIGHT.
    # splitext() only sees the final extension, so shell.php.png looks like a
    # harmless .png to the allowlist below; a double extension is the whole
    # point of that trick, so refuse it before it can reach disk.
    if name.count(".") > 1:
        raise ValidationError(
            _("Filenames with more than one dot are not allowed: ") + name
        )

    ext = os.path.splitext(name)[1].lower()  # [0] returns path+filename

    # Allowlist: accept only the few extensions we know are safe, and reject
    # everything else (never blocklist dangerous ones - that list is never
    # finished). A file with no extension is still allowed, as before.
    if ext not in helpdesk_settings.HELPDESK_VALID_EXTENSIONS and not (
        ext == "" or ext == "."
    ):
        raise ValidationError(_("Unsupported file extension: ") + ext)


def validate_image_content(value):
    """Part C Layer-2 fix: for anything that claims to be an image by its
    extension, decide the type from the CONTENT, not the claim. Decode the bytes
    with Pillow; if they are not actually that image, reject. This is what stops
    a PHP web shell (or an SVG carrying script) renamed to ``evil.png`` from
    being stored just because ``.png`` is on the allowlist. The accepted bytes
    are re-encoded at save time (see helpdesk.lib) so only pixel data survives.
    """
    import os

    from django.core.exceptions import ValidationError

    if not helpdesk_settings.HELPDESK_VALIDATE_ATTACHMENT_TYPES:
        return

    ext = os.path.splitext(os.path.basename(value.name))[1].lower()
    if ext not in (".jpg", ".jpeg", ".png"):
        return

    try:
        from PIL import Image

        value.seek(0)
        with Image.open(value) as img:
            img.verify()  # raises if the bytes are not a valid image
    except ValidationError:
        raise
    except Exception:
        raise ValidationError(_("File is not a valid image."))
    finally:
        try:
            value.seek(0)
        except Exception:
            pass
