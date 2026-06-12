from scansci_pdf.browser_launch import camofox_launch_args


def test_camofox_launch_args_can_disable_system_proxy():
    args = camofox_launch_args({"camofox_no_proxy": True})

    assert "--no-proxy-server" in args
    assert "--disable-features=CrossOriginOpenerPolicy" in args


def test_camofox_launch_args_uses_system_proxy_by_default():
    assert "--no-proxy-server" not in camofox_launch_args({})
