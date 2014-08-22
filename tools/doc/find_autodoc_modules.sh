#!/bin/bash

ZAQAR_DIR='../../zaqar/' # include trailing slash
DOCS_DIR='source'

modules=''
for x in `find ${ZAQAR_DIR} -name '*.py' | grep -v zaqar/tests | grep -v zaqar/bench`; do
    if [ `basename ${x} .py` == "__init__" ] ; then
        continue
    fi
    relative=zaqar.`echo ${x} | sed -e 's$^'${ZAQAR_DIR}'$$' -e 's/.py$//' -e 's$/$.$g'`
    modules="${modules} ${relative}"
done

for mod in ${modules} ; do
  if [ ! -f "${DOCS_DIR}/${mod}.rst" ];
  then
    echo ${mod}
  fi
done