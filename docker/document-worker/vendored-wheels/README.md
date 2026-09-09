# Vendored Document Worker wheel

`odfpy` 1.4.1 is the only locked Document Worker dependency for which PyPI
does not publish a universal wheel. The repository therefore carries the small
pure-Python wheel consumed by the offline image build.

- upstream sdist: `odfpy-1.4.1.tar.gz`
- upstream PyPI SHA-256:
  `db766a6e59c5103212f3cc92ec8dd50a0f3a02790233ed0b52148b70d3c438ec`
- deterministic wheel SHA-256:
  `47943c88ca1ce11e2dd37f3629752680f4332f381b695c3cc1fbbdd322fae313`
- build environment used for the recorded wheel: Python 3.12,
  `SOURCE_DATE_EPOCH=0`, pip 26.1.2, setuptools 82.0.1
- upstream licence: Apache-2.0

The normal CI download path never rebuilds this wheel. It verifies the
versioned SHA-256 and copies it into the ignored build wheelhouse. Updating it
requires an explicit dependency-lock review.
