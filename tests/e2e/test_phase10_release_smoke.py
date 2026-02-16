from ultragravity.cli import build_parser


def test_cli_surface_contains_release_commands():
    parser = build_parser()
    args = parser.parse_args(["status"])
    assert args.command == "status"

    args = parser.parse_args(["logs", "--kind", "all", "--lines", "5"])
    assert args.command == "logs"

    args = parser.parse_args(["policy", "--set", "strict"])
    assert args.command == "policy"
