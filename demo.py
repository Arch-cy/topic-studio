from datetime import datetime
from uuid import uuid4

from models import Evidence, Outline, ResearchRun, Source, Topic

DEMO_REVISION = "badminton-v1"
DEMO_SUBJECT = "羽毛球"
DEMO_AUDIENCE = "业余羽毛球爱好者"
DEMO_FOCUS = "装备消费、双打配合与运动保护"


def sample_run() -> ResearchRun:
    sources = [
        Source(
            id="S1", title="羽毛球拍产品与选拍入口 · YONEX",
            url="https://www.yonex.com/badminton/racquets",
            excerpt="YONEX 产品页列出多个球拍系列及 PRO、TOUR、GAME、PLAY 等不同型号，并提供产品比较和选拍入口。它能说明产品选择存在差异，但不提供‘更贵球拍提高业余胜率’的对照证据。",
            basis="人工核对的样例摘要，非当前实时抓取",
        ),
        Source(
            id="S2", title="双打战术与站位 · Badminton Bible",
            url="https://www.badmintonbible.com/tactics/doubles",
            excerpt="双打战术教程强调围绕进攻机会选择击球，并指出站位需要考虑两人如何覆盖场地，不能只是没有目的地固定左右或前后分工。具体选择还取决于当时的回合情境。",
            basis="人工核对的样例摘要，非当前实时抓取",
        ),
        Source(
            id="S3", title="扭伤与拉伤：症状与求助时机 · NHS",
            url="https://www.nhs.uk/conditions/sprains-and-strains/",
            excerpt="NHS 指南介绍扭伤和拉伤可能出现的疼痛、肿胀、无力及承重困难。疑似受伤时应停止相关运动；疼痛明显或加重、肿胀加重、不能承重等情况需要及时医疗评估。该指南不是羽毛球专项研究，也不能用于判断个人膝痛的原因。",
            basis="人工核对的样例摘要，非当前实时抓取",
        ),
    ]
    topics = [
        Topic(
            id="demo-badminton-1", title="业余羽毛球，千元球拍真比几百元的更容易赢吗？",
            angle="决策", audience="想升级装备的入门与进阶球友",
            why="买拍预算、明星同款和真实手感，是球友容易分享亲身经历的消费选择。可以把‘贵不贵’转化为‘是否适合自己’的具体讨论。",
            tension="更贵的装备可能提供不同的规格和体验，但技术、训练与适配度也会影响表现；价格是否等于胜率值得验证。",
            source_ids=["S1"], caveat="产品页不是独立测评，没有证明价格与胜率的关系。标题中的价位是讨论设定，不是本次市场报价。",
        ),
        Topic(
            id="demo-badminton-2", title="双打输了就怪搭档：是球技不行，还是两个人根本不会站位？",
            angle="争议", audience="经常拼场或更换搭档的业余双打球友",
            why="抢同一个球、中路漏球、前后场分工不清，是有具体场景和不同立场的配合问题，适合用回合复盘代替互相甩锅。",
            tension="失分看起来是最后一拍的失误，问题也可能来自前一拍的选择、补位和沟通；固定分工与动态轮转如何取舍？",
            source_ids=["S2"], caveat="战术教程能提供分析框架，不能据此给某位搭档定责。没有真实回合录像，不应断言某一种站位总是正确。",
        ),
        Topic(
            id="demo-badminton-3", title="打羽毛球膝盖疼，还能戴上护膝继续打吗？",
            angle="实践", audience="打球后反复不适、又舍不得停场的球友",
            why="‘今天还打不打’比笼统讨论运动伤膝更贴近日常选择，也能把护具、训练负荷和受伤信号分开说清楚。",
            tension="想维持运动习惯，不等于可以忽略疼痛；护具的支持作用与继续带伤运动是否安全，是不同的问题。",
            source_ids=["S3"], caveat="一般运动损伤资料不能诊断个人膝痛，也不能证明戴护膝就能安全继续运动。明显或加重的疼痛、肿胀、承重困难应及时就医评估。",
        ),
    ]
    evidence = [
        Evidence(statement="不同系列、不同型号的球拍提供多种选择，但产品目录本身不能证明更高价格带来更高胜率。", source_ids=["S1"], limitation="品牌资料存在商业视角，缺少控制技术水平等因素的对照测试。"),
        Evidence(statement="双打站位需要服务于场地覆盖和回合中的进攻机会，不能只机械地固定左右或前后。", source_ids=["S2"], limitation="战术教学不是对任意一场失利的归因；具体判断需要回合情境。"),
        Evidence(statement="疑似扭伤、拉伤时不能忽略疼痛；疼痛加重、明显肿胀或无法承重等情况需要医疗评估。", source_ids=["S3"], limitation="一般指南不等于羽毛球专项研究，不能据此判断个人伤情或恢复时间。"),
    ]
    return ResearchRun(
        id=uuid4().hex, subject=DEMO_SUBJECT, audience=DEMO_AUDIENCE,
        focus=DEMO_FOCUS, mode="demo",
        created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
        sources=sources, evidence=evidence, topics=topics,
        trace=[
            {"stage": "资料搜集", "detail": "载入装备、双打战术、运动损伤三组参考资料；本轮未调用搜索或模型。", "elapsed": "样例"},
            {"stage": "证据摘要", "detail": "载入人工整理的 3 条证据，并区分产品信息、战术教学与一般健康指南。", "elapsed": "样例"},
            {"stage": "选题分析", "detail": "载入 3 组预先编写的羽毛球讨论话题；未采集热度数据，不代表实时热榜。", "elapsed": "样例"},
        ],
    )


def sample_outline(topic: Topic) -> Outline:
    outlines = {
        "demo-badminton-1": {
            "thesis": "把‘贵拍是否更容易赢’拆成预算、适配和训练三个问题，避免用价格替代对实际需求的判断。",
            "sections": [
                "从一次升级球拍的真实预算决策切入，交代技术水平和当前球拍",
                "对比候选球拍的规格、手感和目标使用场景，不直接按价位分高下",
                "用同一球员、相近球线条件与多次试打记录比较体验，说明样本局限",
                "比较换拍、训练课和日常练习的不同投入方向，避免未经验证的收益排名",
                "给出选拍前要问的三个问题：哪里不适合、能否试打、预算上限是多少",
            ],
            "counterargument": "对于能明确说出适配需求的球友，换拍可能有实际价值；不能把所有装备升级都说成浪费。",
            "checks": ["补充实际售价、球拍规格和独立试打记录。", "区分主观手感改善与胜率变化，不能混用。", "记录技术水平、球线与对手差异，避免把所有变化归因于球拍。"],
        },
        "demo-badminton-2": {
            "thesis": "双打失分的讨论应回到两个人如何覆盖场地、选择击球和沟通，而不是只责怪最后碰球的人。",
            "sections": [
                "以一段中路漏球或两人同时抢球的回合开场，先完整交代前后几拍",
                "解释前后与左右站位分别想解决什么覆盖问题，避免当成永远不变的分工",
                "从击球选择、搭档位置与补位时机三个角度复盘同一回合",
                "比较固定搭档和临时拼场的沟通成本，讨论喊球与责任区域的约定",
                "提出下一场可尝试的一条配合约定，用录像复盘而非凭印象争论",
            ],
            "counterargument": "个人击球能力确实会影响结果，不能把所有失误都解释成站位问题；需要同时看技术执行与配合。",
            "checks": ["取得参与者同意后使用真实回合录像。", "让双方分别描述当时的判断，避免只采用一方说法。", "请有经验的教练核对战术解释，勿用单一回合概括所有水平。"],
        },
        "demo-badminton-3": {
            "thesis": "护膝不能替代对疼痛原因的判断；疑似受伤时应停止诱发疼痛的运动，再决定是否需要专业评估。",
            "sections": [
                "从球友想继续打完一场的情境切入，明确这不是远程诊断",
                "区分疲劳感与需要认真对待的疼痛、肿胀或承重困难，不给出自诊标准",
                "拆开护具、运动负荷、动作与恢复等因素，不把护膝当成继续打球的许可",
                "依据一般损伤指南说明哪些表现需要及时医疗评估，并交代资料适用范围",
                "整理就诊或咨询前可记录的信息：出现时间、诱发动作、是否肿胀及日常活动影响",
            ],
            "counterargument": "不是所有运动后不适都意味着严重损伤，但也不能据此把反复疼痛当作正常训练效果。",
            "checks": ["请运动医学或康复专业人员审阅健康相关表述。", "不要凭个别球友经验推荐护具疗效或承诺恢复时间。", "明显或加重的疼痛、肿胀、无法承重等情况应及时就医评估。"],
        },
    }
    content = outlines.get(topic.id)
    if content:
        return Outline(**content, source_ids=topic.source_ids)
    return Outline(
        thesis=f"围绕“{topic.title}”，先定义判断标准，再用具体案例检验。",
        sections=[f"交代目标读者的困惑：{topic.audience}", f"说明讨论价值：{topic.why}", f"拆开分歧：{topic.tension}", "对照原始来源与真实案例，列出适用条件"],
        counterargument=topic.tension,
        checks=[topic.caveat, "核对原始来源与关键判断之间的关系。"],
        source_ids=topic.source_ids,
    )
