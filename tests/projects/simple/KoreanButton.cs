using Godot;
using Godot.Collections;

public partial class KoreanButton : Button
{
	public override void _Ready()
	{
		Text = "제출";
	}

	public Dictionary _GodotLocatorFormat()
	{
		return new Dictionary
		{
			["attrs"] = new Dictionary { ["greeting"] = "안녕하세요" },
		};
	}
}
