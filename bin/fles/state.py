#!/usr/bin/env python3

import base64

import flask
from fles import app  # noqa
from fles import kratlib  # noqa

KRAT = kratlib.Fles()


@app.route("/", methods=['GET', 'POST'])
@app.route("/state", methods=['GET', 'POST'])
def state():
    """
    Prepare images for display and render the website.

    Returns:
        A Flask rendered template.
    """
    if flask.request.method == 'POST':
        pass

    if flask.request.method == 'GET':
        pass

    hr_img_t = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_hours_temperature.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    hr_img_act = "".join(["data:image/png;base64,",
                          str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_hours_temperature_ac.png",
                                                    "rb"
                                                    ).read()))[2:-1]
                          ])
    hr_img_h = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_hours_humidity.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    hr_img_v = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_hours_voltage.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    hr_img_c = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_hours_compressor.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    # DY
    dy_img_t = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_days_temperature.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    dy_img_act = "".join(["data:image/png;base64,",
                          str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_days_temperature_ac.png",
                                                    "rb"
                                                    ).read()))[2:-1]
                          ])
    dy_img_h = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_days_humidity.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    dy_img_v = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_days_voltage.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    dy_img_c = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_days_compressor.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    # MN
    mn_img_t = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_months_temperature.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    mn_img_act = "".join(["data:image/png;base64,",
                          str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_months_temperature_ac.png",
                                                    "rb"
                                                    ).read()))[2:-1]
                          ])
    mn_img_h = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_months_humidity.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    mn_img_v = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_months_voltage.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])
    mn_img_c = "".join(["data:image/png;base64,",
                        str(base64.b64encode(open("/tmp/kimnaty/site/img/kim_months_compressor.png",
                                                  "rb"
                                                  ).read()))[2:-1]
                        ])

    return flask.render_template('state.html',
                                 hr_img_t=hr_img_t,
                                 hr_img_act=hr_img_act,
                                 hr_img_h=hr_img_h,
                                 hr_img_v=hr_img_v,
                                 hr_img_c=hr_img_c,
                                 dy_img_t=dy_img_t,
                                 dy_img_act=dy_img_act,
                                 dy_img_h=dy_img_h,
                                 dy_img_v=dy_img_v,
                                 dy_img_c=dy_img_c,
                                 mn_img_t=mn_img_t,
                                 mn_img_act=mn_img_act,
                                 mn_img_h=mn_img_h,
                                 mn_img_v=mn_img_v,
                                 mn_img_c=mn_img_c
                                 )
